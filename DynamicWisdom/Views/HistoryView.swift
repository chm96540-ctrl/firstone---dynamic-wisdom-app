import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var store: AppStore

    /// Curated quotes grouped by day, newest first.
    private var groupedByDay: [(day: Date, items: [CuratedQuote])] {
        let groups = Dictionary(grouping: store.curated) { $0.dayKey }
        return groups
            .map { (key, items) -> (Date, [CuratedQuote]) in
                let day = items.first?.day ?? Date()
                let sorted = items.sorted { $0.slot.rawValue < $1.slot.rawValue }
                return (day, sorted)
            }
            .sorted { $0.0 > $1.0 }
    }

    var body: some View {
        NavigationStack {
            Group {
                if store.curated.isEmpty {
                    ContentUnavailableView("No history yet",
                                           systemImage: "clock",
                                           description: Text("Your curated quotes will collect here."))
                } else {
                    List {
                        statsSection
                        ForEach(groupedByDay, id: \.day) { group in
                            Section(group.day.formatted(.dateTime.weekday(.wide).month().day())) {
                                ForEach(group.items) { item in
                                    HistoryRow(item: item) { store.vote($0, on: item) }
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("History")
        }
    }

    private var statsSection: some View {
        let stats = store.voteStats
        return Section {
            HStack {
                stat(value: stats.total, label: "Curated", color: .indigo)
                Divider()
                stat(value: stats.up, label: "Helpful", color: .green)
                Divider()
                stat(value: stats.down, label: "Off-base", color: .red)
            }
            .frame(maxWidth: .infinity)
        }
    }

    private func stat(value: Int, label: String, color: Color) -> some View {
        VStack(spacing: 2) {
            Text("\(value)").font(.title2.bold()).foregroundStyle(color)
            Text(label).font(.caption2).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct HistoryRow: View {
    let item: CuratedQuote
    let onVote: (CuratedQuote.Vote) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Label(item.slot.title, systemImage: item.slot.symbol)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                Spacer()
                voteIndicator
            }
            Text("“\(item.quoteText)”")
                .font(.callout)
            Text("— \(item.quoteAuthor)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
        .swipeActions(edge: .leading) {
            Button { onVote(.up) } label: { Label("Helpful", systemImage: "hand.thumbsup.fill") }
                .tint(.green)
        }
        .swipeActions(edge: .trailing) {
            Button { onVote(.down) } label: { Label("Off-base", systemImage: "hand.thumbsdown.fill") }
                .tint(.red)
        }
    }

    @ViewBuilder private var voteIndicator: some View {
        switch item.vote {
        case .up:
            Image(systemName: "hand.thumbsup.fill").foregroundStyle(.green)
        case .down:
            Image(systemName: "hand.thumbsdown.fill").foregroundStyle(.red)
        case .none:
            EmptyView()
        }
    }
}

#Preview {
    let store = AppStore(library: SampleData.quotes)
    store.addLifeEvent(note: "Training for a marathon, legs are exhausted", mood: .low)
    store.refreshCuration(for: Date())
    return HistoryView().environmentObject(store)
}
