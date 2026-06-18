# Dynamic Wisdom

A "word of the day," but for *your* life. Log what's going on, and Dynamic Wisdom
curates a quote for the **start** and **end** of each day, matched to what you're
actually going through. Vote each one up or down and the app learns which kinds of
wisdom land for you.

Fully **offline** — no account, no network, no API keys. All curation happens
on-device against a bundled, hand-tagged quote library.

## How it works

1. **Log life events** — free-text notes ("Big presentation tomorrow and I'm
   anxious") plus a mood. A keyword lexicon (`ThemeMatcher`) derives *themes* like
   `stress`, `work`, `courage`.
2. **Twice-daily curation** — `CurationEngine` builds a recency-weighted theme
   profile from your recent events and scores every quote by theme overlap, slot
   fit (morning = energizing, evening = reflective), and freshness.
3. **Vote to tune it** — 👍/👎 on each quote feeds `ThemeBiasLearner`, which raises
   or lowers the weight of that quote's themes for future picks.
4. **Reminders** — optional local notifications nudge you at the start and end of
   each day (times configurable in Settings).

## Project structure

```
DynamicWisdom/
├── DynamicWisdomApp.swift        App entry point
├── Models/
│   ├── Theme.swift               The 22 matching dimensions
│   ├── LifeEvent.swift           A logged moment + mood + derived themes
│   ├── Quote.swift               A library quote
│   └── CuratedQuote.swift        A surfaced quote for a day/slot + vote
├── Engine/
│   ├── ThemeMatcher.swift        Free-text → themes (keyword lexicon)
│   └── CurationEngine.swift      Scoring + selection + vote-based learning
├── Store/
│   ├── AppStore.swift            Observable source of truth
│   ├── Persistence.swift         JSON-file persistence
│   ├── QuoteLibrary.swift        Loads quotes.json
│   └── SampleData.swift          Preview-only sample quotes
├── Notifications/
│   └── NotificationManager.swift Twice-daily local reminders
├── Views/
│   ├── RootView.swift            Tab bar
│   ├── TodayView.swift           The two daily cards
│   ├── QuoteCardView.swift       Quote + vote UI
│   ├── AddLifeEventView.swift    Logging form with live theme preview
│   ├── LifeEventsView.swift      History of logged events
│   ├── HistoryView.swift         Past curations + vote stats
│   └── SettingsView.swift        Reminders + how-it-works
├── Resources/
│   └── quotes.json               The curated, tagged quote library
└── Assets.xcassets               App icon + accent color
```

## Requirements

- Xcode 16+
- iOS 17.0+

## Running

Open `DynamicWisdom.xcodeproj` in Xcode, select an iOS 17+ simulator, and run.
The project uses file-system-synchronized groups, so new files added to the
`DynamicWisdom/` folder are picked up automatically.

## Extending the library

Add entries to `DynamicWisdom/Resources/quotes.json`:

```json
{
  "id": "q053",
  "text": "Your quote here.",
  "author": "Someone",
  "themes": ["growth", "hope"],
  "slot": "morning"
}
```

`themes` must use values from `Theme.swift`; `slot` is `morning`, `evening`, or `any`.

## Roadmap ideas

- A Home Screen / Lock Screen widget for the current quote
- Optional AI rewriting of quotes to your situation (hybrid online mode)
- Streaks and weekly reflection summaries
- iCloud sync across devices
