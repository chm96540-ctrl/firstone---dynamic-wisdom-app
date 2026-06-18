import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var store: AppStore
    @State private var showingAddEvent = false

    private var today: Date { Date() }

    private var todays: [CuratedQuote.DaySlot: CuratedQuote] {
        store.curatedQuotes(for: today)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    greeting

                    ForEach(CuratedQuote.DaySlot.allCases) { slot in
                        if let item = todays[slot] {
                            QuoteCardView(
                                item: item,
                                onVote: { store.vote($0, on: item) },
                                onReroll: { store.reroll(slot: slot, day: today) }
                            )
                        }
                    }

                    if todays.isEmpty {
                        emptyState
                    }

                    addEventButton
                }
                .padding()
            }
            .navigationTitle("Today")
            .background(Color(.systemGroupedBackground))
            .sheet(isPresented: $showingAddEvent) {
                AddLifeEventView()
            }
            .refreshable {
                store.refreshCuration(for: today)
            }
        }
    }

    private var greeting: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(Date.now, format: .dateTime.weekday(.wide).day().month(.wide))
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(timeBasedGreeting)
                .font(.largeTitle.bold())
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var timeBasedGreeting: String {
        let hour = Calendar.current.component(.hour, from: Date())
        switch hour {
        case 5..<12: return "Good morning"
        case 12..<17: return "Good afternoon"
        case 17..<22: return "Good evening"
        default: return "Good night"
        }
    }

    private var emptyState: some View {
        ContentUnavailableView {
            Label("No wisdom yet", systemImage: "quote.bubble")
        } description: {
            Text("Log a life event and we'll curate quotes that fit what you're going through.")
        }
        .frame(maxWidth: .infinity)
    }

    private var addEventButton: some View {
        Button {
            showingAddEvent = true
        } label: {
            Label("Log a life event", systemImage: "plus.circle.fill")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 6)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
    }
}

#Preview {
    let store = AppStore(library: SampleData.quotes)
    store.addLifeEvent(note: "Starting a new job on Monday, nervous but excited", mood: .good)
    return TodayView().environmentObject(store)
}
