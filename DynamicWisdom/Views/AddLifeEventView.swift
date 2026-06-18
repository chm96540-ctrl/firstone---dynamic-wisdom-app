import SwiftUI

struct AddLifeEventView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    @State private var note: String = ""
    @State private var mood: LifeEvent.Mood = .neutral
    @State private var date: Date = Date()

    /// Live preview of which themes the engine will derive.
    private var previewThemes: [Theme] {
        ThemeMatcher.themes(forNote: note, mood: mood)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("What's going on?") {
                    TextField("e.g. Big presentation tomorrow and I'm anxious about it",
                              text: $note, axis: .vertical)
                        .lineLimit(3...6)
                }

                Section("How are you feeling?") {
                    Picker("Mood", selection: $mood) {
                        ForEach(LifeEvent.Mood.allCases) { m in
                            Text("\(m.emoji)  \(m.label)").tag(m)
                        }
                    }
                    .pickerStyle(.menu)

                    DatePicker("When", selection: $date)
                }

                if !previewThemes.isEmpty {
                    Section("We'll match wisdom for") {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack {
                                ForEach(previewThemes, id: \.self) { theme in
                                    Label(theme.title, systemImage: theme.symbol)
                                        .font(.caption.weight(.medium))
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 6)
                                        .background(Capsule().fill(Color.indigo.opacity(0.12)))
                                        .foregroundStyle(.indigo)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Log Life Event")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        store.addLifeEvent(note: note, mood: mood, date: date)
                        dismiss()
                    }
                    .disabled(note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }
}

#Preview {
    AddLifeEventView()
        .environmentObject(AppStore(library: SampleData.quotes))
}
