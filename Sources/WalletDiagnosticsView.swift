import SwiftUI

struct WalletDiagnosticsView: View {
    @ObservedObject var vm: AppViewModel
    @State private var expanded = false

    private var paymentSummary: String {
        vm.walletCatalog.paymentStatus == "matched" ? "\(vm.pendingPaymentCards.count) payment entries" : "payment count unavailable"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("\(vm.currentVerifiedCardIDs.count) matched in this scan · \(vm.cards.count - vm.currentVerifiedCardIDs.count) saved IDs hidden")
                        .font(.caption).fontWeight(.semibold)
                    Text("Includes live IDs and payment cards from a cache matched by a live ID")
                        .font(.caption2).foregroundStyle(.secondary)
                }
                Spacer()
                Button(vm.isReadingWalletCache ? "Reading…" : "Read Cache") { vm.refreshWalletCatalog() }
                    .disabled(vm.isReadingWalletCache || vm.device?.connected != true)
                    .help("Read this Mac's existing Wallet cache. This does not force iCloud to refresh it.")
                Button("Reconnect") { vm.checkDevice() }
                    .disabled(vm.isCheckingDevice || vm.isFlashing)
            }
            Text(vm.scannerMessage)
                .font(.caption2).foregroundStyle(.secondary)
            DisclosureGroup(isExpanded: $expanded) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Open each missing card in the iPhone Wallet app, then scan again. For payment cards, you can also double-click the side button and authenticate. Unseen cache entries may be old, removed, or from a different Wallet library.")
                        if let date = vm.walletCatalog.cacheUpdatedAt {
                            Text("Payment cache date: \(date.prefix(10))")
                                .foregroundStyle(.secondary)
                        }
                        ForEach(vm.walletCatalog.warnings, id: \.self) { warning in
                            Label(warning, systemImage: "info.circle")
                        }
                        if vm.walletCatalog.paymentStatus == "matched" {
                            Text("Payment cache: \(vm.walletCatalog.payments.count) entries · \(vm.pendingPaymentCards.count) to confirm")
                                .fontWeight(.semibold)
                            ForEach(vm.pendingPaymentCards) { card in pendingRow(card) }
                            if vm.pendingPaymentCards.isEmpty {
                                Text("All entries in this payment cache have been scanned. Other cards may still be missing from the cache.")
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Text("Mac membership / ticket cache: \(vm.pendingMembershipCards.count) to confirm on this iPhone")
                            .fontWeight(.semibold)
                        ForEach(vm.pendingMembershipCards) { card in pendingRow(card) }
                        if vm.walletCatalog.memberships.isEmpty {
                            Text("No membership metadata available in this Mac's cache. This does not mean the iPhone has no membership cards.")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 6)
                    .font(.caption)
                }
                .frame(maxHeight: 180)
            } label: {
                Text("Check missing cards · \(paymentSummary) · \(vm.pendingMembershipCards.count) Mac passes to confirm")
                    .font(.caption)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .controlSize(.small)
    }

    private func pendingRow(_ card: WalletCachedCard) -> some View {
        HStack {
            Image(systemName: "questionmark.circle").foregroundStyle(.orange)
            Text(card.name)
            Text("…" + card.id.suffix(6))
                .font(.system(.caption2, design: .monospaced)).foregroundStyle(.secondary)
            Spacer()
            Text("Not scan-confirmed").foregroundStyle(.secondary)
        }
    }
}
