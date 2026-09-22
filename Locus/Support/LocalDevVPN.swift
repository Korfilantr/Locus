import Darwin
import Foundation
import UIKit

enum LocalDevVPN {
    static let appStoreURL = URL(string: "https://apps.apple.com/us/app/localdevvpn/id6755608044")!
    static let detectURL = URL(string: "localdevvpn://")!

    /// Starts the tunnel, then returns to locbridge via `locbridge://`.
    static let enableURL = URL(string: "localdevvpn://enable?scheme=locbridge")!

    static var isInstalled: Bool {
        UIApplication.shared.canOpenURL(detectURL)
    }

    /// LocalDevVPN puts the tunnel network on a `10.7.0.x` (or custom) utun when connected.
    static var isConnected: Bool {
        let addresses = ipv4InterfaceAddresses()
        let target = TunnelConfig.targetIP
        if addresses.contains(target) { return true }

        let parts = target.split(separator: ".")
        guard parts.count == 4 else { return false }
        let prefix = parts.dropLast().joined(separator: ".") + "."
        return addresses.contains { $0.hasPrefix(prefix) }
    }

    static func openInstalled() {
        UIApplication.shared.open(enableURL)
    }

    static func openAppStore() {
        UIApplication.shared.open(appStoreURL)
    }

    /// Open LocalDevVPN to connect if installed; otherwise App Store.
    static func openOrInstall() {
        if isInstalled {
            openInstalled()
        } else {
            openAppStore()
        }
    }

    private static func ipv4InterfaceAddresses() -> [String] {
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddr) == 0, let first = ifaddr else { return [] }
        defer { freeifaddrs(ifaddr) }

        var results: [String] = []
        var ptr: UnsafeMutablePointer<ifaddrs>? = first
        while let current = ptr {
            let interface = current.pointee
            if interface.ifa_addr.pointee.sa_family == UInt8(AF_INET) {
                var host = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                let nameLen = socklen_t(MemoryLayout<sockaddr_in>.size)
                if getnameinfo(
                    interface.ifa_addr,
                    nameLen,
                    &host,
                    socklen_t(host.count),
                    nil,
                    0,
                    NI_NUMERICHOST
                ) == 0 {
                    results.append(String(cString: host))
                }
            }
            ptr = interface.ifa_next
        }
        return results
    }
}

/// Opens LocalDevVPN when locbridge comes to the foreground without a tunnel.
/// LocalDevVPN connects, then returns here through `locbridge://`.
@MainActor
enum VPNAutoConnect {
    nonisolated static let defaultsKey = "locbridge.autoConnectVPN"

    /// On by default; the switch lives in Settings › Tunnel.
    static var isEnabled: Bool {
        UserDefaults.standard.object(forKey: defaultsKey) as? Bool ?? true
    }

    /// Set while on-device pairing runs: pairing sends the user to Settings and
    /// back, and bouncing them into LocalDevVPN then would break the flow.
    static var isSuspended = false

    /// Long enough that a tunnel which is slow to come up can't cause a loop
    /// of locbridge and LocalDevVPN opening each other.
    private static let cooldown: TimeInterval = 30
    private static var lastAttempt: Date?

    static func connectIfNeeded() async {
        guard isEnabled, !isSuspended, LocalDevVPN.isInstalled else { return }
        // Coming back from LocalDevVPN, the tunnel interface can take a moment to appear.
        try? await Task.sleep(nanoseconds: 1_200_000_000)
        guard UIApplication.shared.applicationState == .active,
              !isSuspended,
              !LocalDevVPN.isConnected else { return }
        if let last = lastAttempt, Date().timeIntervalSince(last) < cooldown { return }
        lastAttempt = Date()
        LocalDevVPN.openInstalled()
    }
}
