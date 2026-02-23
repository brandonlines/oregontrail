import SwiftUI

struct ContentView: View {
    @StateObject private var vm = GameViewModel()

    @State private var selectedProfession: Profession = .carpenter
    @State private var selectedDepartureMonth = 2
    @State private var leaderName = ""

    @State private var travelDays = 7
    @State private var restDays = 2

    @State private var showShop = false

    var body: some View {
        NavigationStack {
            Group {
                if !vm.gameStarted {
                    setupView
                } else {
                    gameView
                }
            }
            .navigationTitle("Oregon Trail")
            .sheet(isPresented: $showShop) {
                shopView
            }
            .onChange(of: vm.pendingFortShop) { _, newValue in
                if newValue {
                    showShop = true
                    vm.pendingFortShop = false
                }
            }
        }
    }

    private var setupView: some View {
        Form {
            Section("Party") {
                TextField("Leader name", text: $leaderName)
            }

            Section("Profession") {
                Picker("Choose", selection: $selectedProfession) {
                    ForEach(Profession.all) { profession in
                        Text("\(profession.name) ($\(profession.startingMoney))").tag(profession)
                    }
                }
                .pickerStyle(.segmented)
            }

            Section("Departure") {
                Picker("Month", selection: $selectedDepartureMonth) {
                    ForEach(0..<6, id: \.self) { idx in
                        Text(vm.months[idx]).tag(idx)
                    }
                }
            }

            Section {
                Button("Start Journey") {
                    vm.startGame(
                        profession: selectedProfession,
                        departureMonthIndex: selectedDepartureMonth,
                        leaderName: leaderName.trimmingCharacters(in: .whitespacesAndNewlines)
                    )
                }
            }
        }
    }

    private var gameView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                statusCard
                inventoryCard
                controlsCard
                logCard
            }
            .padding()
        }
    }

    private var statusCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Date: \(vm.dateString)  |  Weather: \(vm.weather.name)")
            Text("Miles: \(vm.milesTraveled)/\(vm.totalMiles)")
            Text("Health: \(vm.party.health)  |  Morale: \(vm.party.morale)")
            Text("Pace: \(vm.pace.rawValue.capitalized)  |  Rations: \(vm.rations.rawValue.capitalized)")
            Text("Profession: \(vm.profession.name)")

            if vm.gameEnded {
                Divider()
                if vm.victory {
                    Text("Arrived in Oregon. Final score: \(vm.finalScore)")
                        .fontWeight(.semibold)
                        .foregroundStyle(.green)
                } else {
                    Text("Your party perished from \(vm.deathReason).")
                        .fontWeight(.semibold)
                        .foregroundStyle(.red)
                }

                Button("Start New Game") {
                    vm.gameStarted = false
                }
                .padding(.top, 4)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var inventoryCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Money: $\(vm.inventory.money)")
            Text("Food: \(vm.inventory.food) lbs")
            Text("Ammo: \(vm.inventory.ammo)")
            Text("Clothing: \(vm.inventory.clothing)")
            Text("Spare Parts: \(vm.inventory.spareParts)")
            Text("Medicine: \(vm.inventory.medicine)")
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var controlsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Picker("Pace", selection: $vm.pace) {
                ForEach(Pace.allCases) { pace in
                    Text(pace.rawValue.capitalized).tag(pace)
                }
            }
            .pickerStyle(.segmented)
            .disabled(vm.gameEnded)

            Picker("Rations", selection: $vm.rations) {
                ForEach(Rations.allCases) { rations in
                    Text(rations.rawValue.capitalized).tag(rations)
                }
            }
            .pickerStyle(.segmented)
            .disabled(vm.gameEnded)

            Stepper("Travel days: \(travelDays)", value: $travelDays, in: 3...14)
            Button("Travel") { vm.travel(days: travelDays) }
                .buttonStyle(.borderedProminent)
                .disabled(vm.gameEnded)

            Stepper("Rest days: \(restDays)", value: $restDays, in: 1...5)
            Button("Rest") { vm.rest(days: restDays) }
                .buttonStyle(.bordered)
                .disabled(vm.gameEnded)

            HStack {
                Button("Hunt") { vm.hunt() }
                    .buttonStyle(.bordered)
                    .disabled(vm.gameEnded)

                Button("Find Shop") {
                    if vm.tryNearbyShop() {
                        showShop = true
                    }
                }
                .buttonStyle(.bordered)
                .disabled(vm.gameEnded)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var logCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Trail Log")
                .font(.headline)

            if vm.eventLog.isEmpty {
                Text("No events yet.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(vm.eventLog.prefix(12), id: \.self) { line in
                    Text(line)
                        .font(.caption)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var shopView: some View {
        NavigationStack {
            List {
                Section("Money: $\(vm.inventory.money)") {
                    ForEach(ShopItem.allCases) { item in
                        ShopRow(item: item) { quantity in
                            vm.buy(item: item, quantity: quantity)
                        }
                    }
                }
            }
            .navigationTitle("General Store")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { showShop = false }
                }
            }
        }
    }
}

private struct ShopRow: View {
    let item: ShopItem
    let onBuy: (Int) -> Void

    @State private var quantity = 1

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("\(item.title) ($\(item.price) each)")
                .font(.subheadline)
                .fontWeight(.medium)

            Stepper("Qty: \(quantity)", value: $quantity, in: 1...100)

            Button("Buy") {
                onBuy(quantity)
            }
            .buttonStyle(.bordered)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    ContentView()
}
