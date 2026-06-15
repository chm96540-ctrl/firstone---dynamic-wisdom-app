import Foundation

/// A tiny in-memory quote set used only by SwiftUI previews so they don't depend
/// on bundle resource loading.
enum SampleData {
    static let quotes: [Quote] = [
        Quote(id: "s1",
              text: "The best way out is always through.",
              author: "Robert Frost",
              themes: [.perseverance, .resilience, .courage],
              slot: .morning),
        Quote(id: "s2",
              text: "What we achieve inwardly will change outer reality.",
              author: "Plutarch",
              themes: [.growth, .reflection],
              slot: .evening),
        Quote(id: "s3",
              text: "You don't have to control your thoughts. You just have to stop letting them control you.",
              author: "Dan Millman",
              themes: [.stress, .calm, .focus],
              slot: .any),
        Quote(id: "s4",
              text: "Gratitude turns what we have into enough.",
              author: "Anonymous",
              themes: [.gratitude, .calm],
              slot: .evening),
        Quote(id: "s5",
              text: "Every new beginning comes from some other beginning's end.",
              author: "Seneca",
              themes: [.beginnings, .change, .hope],
              slot: .morning)
    ]
}
