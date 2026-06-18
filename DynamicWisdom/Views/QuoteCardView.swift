import SwiftUI

/// The hero card that displays a curated quote and the up/down vote controls.
struct QuoteCardView: View {
    let item: CuratedQuote
    let onVote: (CuratedQuote.Vote) -> Void
    let onReroll: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            header

            Text("“\(item.quoteText)”")
                .font(.title2.weight(.semibold))
                .fixedSize(horizontal: false, vertical: true)
                .lineSpacing(4)

            Text("— \(item.quoteAuthor)")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if !item.themes.isEmpty {
                themeChips
            }

            if !item.basedOnEventNotes.isEmpty {
                basedOn
            }

            Divider().padding(.vertical, 4)

            votingRow
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(Color(.secondarySystemBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .strokeBorder(borderColor, lineWidth: item.vote == .none ? 0 : 2)
        )
    }

    private var header: some View {
        HStack {
            Label(item.slot.greeting, systemImage: item.slot.symbol)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Spacer()
            Button(action: onReroll) {
                Image(systemName: "arrow.triangle.2.circlepath")
                    .font(.callout)
            }
            .buttonStyle(.borderless)
            .accessibilityLabel("Show a different quote")
        }
    }

    private var themeChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(item.themes, id: \.self) { theme in
                    Label(theme.title, systemImage: theme.symbol)
                        .font(.caption2.weight(.medium))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Capsule().fill(Color.indigo.opacity(0.12)))
                        .foregroundStyle(.indigo)
                }
            }
        }
    }

    private var basedOn: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Based on")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.tertiary)
            ForEach(item.basedOnEventNotes.prefix(2), id: \.self) { note in
                Text("• \(note)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
    }

    private var votingRow: some View {
        HStack(spacing: 12) {
            Text("How applicable was this?")
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
            voteButton(.down, symbol: "hand.thumbsdown.fill", tint: .red)
            voteButton(.up, symbol: "hand.thumbsup.fill", tint: .green)
        }
    }

    private func voteButton(_ vote: CuratedQuote.Vote, symbol: String, tint: Color) -> some View {
        Button {
            onVote(vote)
        } label: {
            Image(systemName: symbol)
                .font(.title3)
                .foregroundStyle(item.vote == vote ? .white : tint)
                .frame(width: 44, height: 44)
                .background(
                    Circle().fill(item.vote == vote ? tint : tint.opacity(0.12))
                )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(vote == .up ? "Mark applicable" : "Mark not applicable")
    }

    private var borderColor: Color {
        switch item.vote {
        case .up: return .green
        case .down: return .red
        case .none: return .clear
        }
    }
}

#Preview {
    QuoteCardView(
        item: CuratedQuote(
            quoteID: "x",
            quoteText: "The best way out is always through.",
            quoteAuthor: "Robert Frost",
            themes: [.perseverance, .resilience],
            slot: .morning,
            day: Date(),
            basedOnEventNotes: ["Big deadline at work tomorrow"]
        ),
        onVote: { _ in },
        onReroll: {}
    )
    .padding()
}
