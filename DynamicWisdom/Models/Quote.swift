import Foundation

/// A single piece of wisdom from the bundled library (`quotes.json`).
struct Quote: Identifiable, Codable, Hashable {
    /// When this quote is best surfaced.
    enum Slot: String, Codable {
        case morning   // forward-looking, energizing
        case evening   // reflective, settling
        case any       // works either time
    }

    var id: String
    var text: String
    var author: String
    var themes: [Theme]
    var slot: Slot

    enum CodingKeys: String, CodingKey {
        case id, text, author, themes, slot
    }

    init(id: String, text: String, author: String, themes: [Theme], slot: Slot) {
        self.id = id
        self.text = text
        self.author = author
        self.themes = themes
        self.slot = slot
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        text = try c.decode(String.self, forKey: .text)
        author = try c.decodeIfPresent(String.self, forKey: .author) ?? "Unknown"
        themes = try c.decodeIfPresent([Theme].self, forKey: .themes) ?? []
        slot = try c.decodeIfPresent(Slot.self, forKey: .slot) ?? .any
    }
}
