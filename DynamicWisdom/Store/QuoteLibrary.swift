import Foundation

/// Loads the bundled quote bank from `quotes.json`.
enum QuoteLibrary {
    static func load() -> [Quote] {
        guard let url = Bundle.main.url(forResource: "quotes", withExtension: "json") else {
            assertionFailure("quotes.json missing from bundle")
            return []
        }
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode([Quote].self, from: data)
        } catch {
            assertionFailure("Failed to decode quotes.json: \(error)")
            return []
        }
    }
}
