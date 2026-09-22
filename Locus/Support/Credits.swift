import SwiftUI

/// Who made this build. Shown on the welcome page, the pairing screens and in Settings.
enum AppCredits {
    static let author = "Korfilantr"
    static let collaborator = "Claude"
    static let madeBy = "Made by \(author) & \(collaborator)"
    /// Locus is MIT-licensed; its notice travels with the app.
    static let upstream = "Built on Locus by the Locus contributors (MIT). Location injection uses the MIT-licensed idevice FFI."
}

/// A quiet "Made by …" line for the setup and pairing screens.
struct CreditsLine: View {
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "sparkles")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(LocusTheme.accent)
            Text(AppCredits.madeBy)
                .font(.caption.weight(.medium))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .locusGlass(.clear, in: Capsule())
        .accessibilityElement(children: .combine)
    }
}
