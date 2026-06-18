import Foundation

/// Simple, robust JSON-file persistence in the app's Documents directory.
/// Chosen over SwiftData/CoreData to keep the project dependency-free and the
/// data model trivially inspectable.
struct JSONStore<T: Codable> {
    let filename: String

    private var url: URL {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return dir.appendingPathComponent(filename)
    }

    func load() -> T? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder.appDecoder.decode(T.self, from: data)
    }

    func save(_ value: T) {
        guard let data = try? JSONEncoder.appEncoder.encode(value) else { return }
        try? data.write(to: url, options: [.atomic])
    }
}

extension JSONDecoder {
    static let appDecoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
}

extension JSONEncoder {
    static let appEncoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        e.outputFormatting = [.prettyPrinted, .sortedKeys]
        return e
    }()
}
