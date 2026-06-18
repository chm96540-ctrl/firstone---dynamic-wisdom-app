import Foundation
import UserNotifications

/// Schedules the twice-daily reminders that nudge the user to read their
/// curated quote (start of day) and reflect / vote (end of day).
enum NotificationManager {

    static func requestAuthorization() async -> Bool {
        do {
            return try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    static func authorizationStatus() async -> UNAuthorizationStatus {
        await UNUserNotificationCenter.current().notificationSettings().authorizationStatus
    }

    /// Reschedule both daily reminders to match the current settings.
    static func reschedule(with settings: AppSettings) {
        let center = UNUserNotificationCenter.current()
        center.removePendingNotificationRequests(withIdentifiers: [Identifier.morning, Identifier.evening])

        guard settings.notificationsEnabled else { return }

        schedule(id: Identifier.morning,
                 hour: settings.morningHour,
                 minute: settings.morningMinute,
                 title: "Your morning wisdom is ready",
                 body: "A quote curated from what's going on in your life. Start strong.")

        schedule(id: Identifier.evening,
                 hour: settings.eveningHour,
                 minute: settings.eveningMinute,
                 title: "End-of-day reflection",
                 body: "Read tonight's quote and rate how the day's wisdom landed.")
    }

    static func cancelAll() {
        UNUserNotificationCenter.current()
            .removePendingNotificationRequests(withIdentifiers: [Identifier.morning, Identifier.evening])
    }

    // MARK: - Private

    private enum Identifier {
        static let morning = "dynamicwisdom.daily.morning"
        static let evening = "dynamicwisdom.daily.evening"
    }

    private static func schedule(id: String, hour: Int, minute: Int, title: String, body: String) {
        var components = DateComponents()
        components.hour = hour
        components.minute = minute

        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: true)
        let request = UNNotificationRequest(identifier: id, content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(request)
    }
}
