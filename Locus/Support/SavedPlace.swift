import CoreLocation
import Foundation

struct SavedPlace: Identifiable, Codable, Equatable {
    var id: String { "\(latitude),\(longitude)" }
    var name: String
    var latitude: Double
    var longitude: Double

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }

    static func load(key: String) -> [SavedPlace] {
        guard let data = UserDefaults.standard.data(forKey: key),
              let decoded = try? JSONDecoder().decode([SavedPlace].self, from: data) else {
            return []
        }
        return decoded
    }

    /// Reads a JSON list of `{"name", "latitude", "longitude"}` objects: the
    /// format of the locbridge server's presets.json and of this app's own list.
    static func decodeList(from data: Data) throws -> [SavedPlace] {
        let decoded: [SavedPlace]
        do {
            decoded = try JSONDecoder().decode([SavedPlace].self, from: data)
        } catch {
            throw NSError(domain: "locbridge", code: 10, userInfo: [
                NSLocalizedDescriptionKey: "That isn't a list of places. Expected JSON like [{\"name\": \"Home\", \"latitude\": 45.8, \"longitude\": 15.9}]."
            ])
        }
        let valid = decoded.filter {
            !$0.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                && (-90...90).contains($0.latitude)
                && (-180...180).contains($0.longitude)
        }
        guard !valid.isEmpty else {
            throw NSError(domain: "locbridge", code: 11, userInfo: [
                NSLocalizedDescriptionKey: "The list has no usable places."
            ])
        }
        return valid
    }

    static func save(_ places: [SavedPlace], key: String) {
        if let data = try? JSONEncoder().encode(places) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }
}
