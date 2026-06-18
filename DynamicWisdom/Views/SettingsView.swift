import SwiftUI
import UIKit

struct SettingsView: View {
    @EnvironmentObject private var store: AppStore
    @State private var draft: AppSettings = .default
    @State private var authDenied = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Toggle("Twice-daily reminders", isOn: $draft.notificationsEnabled)
                } footer: {
                    Text("Get nudged to read your morning quote and reflect on the day's wisdom each evening.")
                }

                if draft.notificationsEnabled {
                    Section("Reminder times") {
                        timePicker("Start of day", hour: $draft.morningHour, minute: $draft.morningMinute)
                        timePicker("End of day", hour: $draft.eveningHour, minute: $draft.eveningMinute)
                    }
                }

                Section("How it works") {
                    infoRow(symbol: "list.bullet.rectangle.portrait",
                            title: "Log life events",
                            detail: "Free-text notes about what's going on, tagged by mood.")
                    infoRow(symbol: "wand.and.stars",
                            title: "Curated twice daily",
                            detail: "We match quotes to your recent events — energizing in the morning, reflective at night.")
                    infoRow(symbol: "hand.thumbsup",
                            title: "Vote to tune it",
                            detail: "Up/down votes teach the app which themes resonate with you.")
                }

                Section {
                    LabeledContent("Quotes in library", value: "\(store.library.count)")
                    LabeledContent("Life events logged", value: "\(store.lifeEvents.count)")
                }
            }
            .navigationTitle("Settings")
            .onAppear { draft = store.settings }
            .onChange(of: draft) { _, new in apply(new) }
            .alert("Notifications are off", isPresented: $authDenied) {
                Button("Open Settings") {
                    if let url = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(url)
                    }
                }
                Button("Not now", role: .cancel) { }
            } message: {
                Text("Enable notifications for Dynamic Wisdom in iOS Settings to receive your daily reminders.")
            }
        }
    }

    private func apply(_ new: AppSettings) {
        store.updateSettings(new)
        Task {
            if new.notificationsEnabled {
                let granted = await NotificationManager.requestAuthorization()
                if granted {
                    NotificationManager.reschedule(with: new)
                } else {
                    authDenied = true
                    draft.notificationsEnabled = false
                }
            } else {
                NotificationManager.cancelAll()
            }
        }
    }

    private func timePicker(_ label: String, hour: Binding<Int>, minute: Binding<Int>) -> some View {
        DatePicker(label, selection: Binding(
            get: {
                Calendar.current.date(from: DateComponents(hour: hour.wrappedValue, minute: minute.wrappedValue)) ?? Date()
            },
            set: { newDate in
                let comps = Calendar.current.dateComponents([.hour, .minute], from: newDate)
                hour.wrappedValue = comps.hour ?? hour.wrappedValue
                minute.wrappedValue = comps.minute ?? minute.wrappedValue
            }
        ), displayedComponents: .hourAndMinute)
    }

    private func infoRow(symbol: String, title: String, detail: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: symbol)
                .font(.title3)
                .foregroundStyle(.indigo)
                .frame(width: 28)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.subheadline.weight(.semibold))
                Text(detail).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}

#Preview {
    SettingsView().environmentObject(AppStore(library: SampleData.quotes))
}
