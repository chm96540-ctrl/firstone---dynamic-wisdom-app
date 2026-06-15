import SwiftUI

@main
struct DynamicWisdomApp: App {
    @StateObject private var store = AppStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .tint(.indigo)
                .onAppear {
                    // Make sure today's picks exist whenever the app opens.
                    store.refreshCuration(for: Date())
                }
        }
    }
}
