import SwiftUI

struct LifeEventsView: View {
    @EnvironmentObject private var store: AppStore
    @State private var showingAddEvent = false

    var body: some View {
        NavigationStack {
            Group {
                if store.lifeEvents.isEmpty {
                    ContentUnavailableView {
                        Label("No life events yet", systemImage: "tray")
                    } description: {
                        Text("Tap + to log what's happening. The more you share, the more relevant your daily wisdom becomes.")
                    } actions: {
                        Button("Log your first event") { showingAddEvent = true }
                            .buttonStyle(.borderedProminent)
                    }
                } else {
                    List {
                        ForEach(store.lifeEvents) { event in
                            LifeEventRow(event: event)
                        }
                        .onDelete(perform: store.deleteLifeEvents)
                    }
                }
            }
            .navigationTitle("Life")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showingAddEvent = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingAddEvent) {
                AddLifeEventView()
            }
        }
    }
}

private struct LifeEventRow: View {
    let event: LifeEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(event.mood.emoji)
                Text(event.note)
                    .font(.body)
                Spacer()
            }
            HStack {
                Text(event.date, format: .dateTime.weekday().month().day().hour().minute())
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Spacer()
                ForEach(event.themes.prefix(3), id: \.self) { theme in
                    Image(systemName: theme.symbol)
                        .font(.caption2)
                        .foregroundStyle(.indigo)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    let store = AppStore(library: SampleData.quotes)
    store.addLifeEvent(note: "Lost my grandfather this week, taking it hard", mood: .rough)
    store.addLifeEvent(note: "Landed the promotion I've been working toward!", mood: .great)
    return LifeEventsView().environmentObject(store)
}
