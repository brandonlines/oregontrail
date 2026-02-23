import Foundation

@MainActor
final class GameViewModel: ObservableObject {
    @Published var totalMiles: Int = 2000
    @Published var milesTraveled: Int = 0
    @Published var monthIndex: Int = 0
    @Published var day: Int = 1

    @Published var party = Party()
    @Published var inventory = Inventory()
    @Published var profession: Profession = .carpenter

    @Published var pace: Pace = .steady
    @Published var rations: Rations = .meager

    @Published var eventLog: [String] = []
    @Published var gameStarted = false
    @Published var gameEnded = false
    @Published var victory = false
    @Published var deathReason = ""

    @Published var pendingFortShop = false

    private var lastLandmarkIndex = -1

    let months = ["March", "April", "May", "June", "July", "August", "September", "October", "November"]

    let weatherByMonth: [String: Weather] = [
        "March": Weather(name: "Cold", milesFactor: 0.85),
        "April": Weather(name: "Cool", milesFactor: 0.95),
        "May": Weather(name: "Mild", milesFactor: 1.05),
        "June": Weather(name: "Warm", milesFactor: 1.10),
        "July": Weather(name: "Hot", milesFactor: 1.05),
        "August": Weather(name: "Hot", milesFactor: 1.00),
        "September": Weather(name: "Mild", milesFactor: 0.95),
        "October": Weather(name: "Cool", milesFactor: 0.90),
        "November": Weather(name: "Cold", milesFactor: 0.80)
    ]

    let landmarks: [Landmark] = [
        Landmark(miles: 120, name: "Kansas River", hasFort: false),
        Landmark(miles: 310, name: "Big Blue River", hasFort: false),
        Landmark(miles: 540, name: "Fort Kearney", hasFort: true),
        Landmark(miles: 800, name: "Chimney Rock", hasFort: false),
        Landmark(miles: 1030, name: "Fort Laramie", hasFort: true),
        Landmark(miles: 1280, name: "Independence Rock", hasFort: false),
        Landmark(miles: 1530, name: "South Pass", hasFort: false),
        Landmark(miles: 1770, name: "Fort Hall", hasFort: true),
        Landmark(miles: 2000, name: "Willamette Valley", hasFort: false)
    ]

    var dateString: String {
        "\(months[monthIndex]) \(day)"
    }

    var weather: Weather {
        weatherByMonth[months[monthIndex], default: Weather(name: "Mild", milesFactor: 1.0)]
    }

    var finalScore: Int {
        let base = party.health + party.morale
        let supplies = (inventory.food / 5) + (inventory.money / 10) + (inventory.medicine * 10)
        return Int(Double(base + supplies) * profession.scoreBonus)
    }

    func startGame(profession: Profession, departureMonthIndex: Int, leaderName: String) {
        self.profession = profession
        monthIndex = max(0, min(departureMonthIndex, 5))
        day = 1
        milesTraveled = 0
        lastLandmarkIndex = -1

        party = Party(
            names: [leaderName.isEmpty ? "You" : leaderName, "Alex", "Sam", "Jordan", "Casey"],
            health: 100,
            morale: 75,
            alive: true
        )

        inventory = Inventory(
            money: profession.startingMoney,
            food: 250,
            ammo: 30,
            clothing: 4,
            spareParts: 1,
            medicine: 0
        )

        pace = .steady
        rations = .meager
        eventLog = ["Journey started as a \(profession.name)."]
        gameStarted = true
        gameEnded = false
        victory = false
        deathReason = ""
        pendingFortShop = false
    }

    func travel(days: Int) {
        guard canAct else { return }

        let tripDays = clamp(days, lo: 3, hi: 14)
        let foodNeeded = rations.foodPerDay * tripDays
        inventory.food = max(0, inventory.food - foodNeeded)

        advanceDays(tripDays)

        let miles = Int(Double(pace.milesPerDay * tripDays) * weather.milesFactor)
        milesTraveled = min(totalMiles, milesTraveled + miles)

        applyDailyWear(days: tripDays)
        checkStarvation()
        maybeRandomEvents()
        handleLandmark()
        checkEndConditions()

        log("Traveled \(tripDays) days and covered \(miles) miles.")
    }

    func rest(days: Int) {
        guard canAct else { return }

        let restDays = clamp(days, lo: 1, hi: 5)
        advanceDays(restDays)
        inventory.food = max(0, inventory.food - (rations.foodPerDay * restDays))
        party.health = clamp(party.health + (4 * restDays), lo: 0, hi: 100)
        party.morale = clamp(party.morale + (5 * restDays), lo: 0, hi: 100)
        checkStarvation()
        checkEndConditions()

        log("Rested for \(restDays) days.")
    }

    func hunt() {
        guard canAct else { return }

        guard inventory.ammo > 0 else {
            log("No ammo available for hunting.")
            return
        }

        let spent = min(inventory.ammo, Int.random(in: 5...14))
        inventory.ammo -= spent

        let success = Int.random(in: 0...100) < 65
        if !success {
            party.morale = clamp(party.morale - 4, lo: 0, hi: 100)
            log("Unsuccessful hunt. Ammo spent: \(spent).")
            return
        }

        let gain = Int.random(in: 80...220)
        let foodCap = 1000
        let newFood = min(foodCap, inventory.food + gain)
        let actualGain = newFood - inventory.food
        inventory.food = newFood
        party.morale = clamp(party.morale + 6, lo: 0, hi: 100)

        log("Successful hunt. Ammo used: \(spent). Food gained: \(actualGain).")
    }

    func tryNearbyShop() -> Bool {
        guard canAct else { return false }

        if Double.random(in: 0...1) < 0.35 {
            log("You found a nearby trading post.")
            return true
        }

        log("No town with a trading post nearby.")
        return false
    }

    func buy(item: ShopItem, quantity: Int) {
        guard quantity > 0 else { return }

        let cost = item.price * quantity
        guard inventory.money >= cost else {
            log("Cannot afford \(quantity) \(item.title.lowercased()).")
            return
        }

        inventory.money -= cost
        switch item {
        case .food: inventory.food += quantity
        case .ammo: inventory.ammo += quantity
        case .clothing: inventory.clothing += quantity
        case .spareParts: inventory.spareParts += quantity
        case .medicine: inventory.medicine += quantity
        }

        log("Bought \(quantity) \(item.title.lowercased()) for $\(cost).")
    }

    private var canAct: Bool {
        gameStarted && !gameEnded && party.alive
    }

    private func advanceDays(_ days: Int) {
        day += days
        while day > 30 {
            day -= 30
            monthIndex = min(monthIndex + 1, months.count - 1)
        }
    }

    private func applyDailyWear(days: Int) {
        var healthDelta = 0
        var moraleDelta = 0

        switch rations {
        case .bare:
            healthDelta -= 5 * days
            moraleDelta -= 3 * days
        case .meager:
            healthDelta -= 2 * days
            moraleDelta -= 1 * days
        case .filling:
            healthDelta += 1 * days
            moraleDelta += 1 * days
        }

        switch pace {
        case .grueling:
            healthDelta -= 4 * days
            moraleDelta -= 2 * days
        case .steady:
            healthDelta -= 1 * days
        case .slow:
            break
        }

        if weather.name == "Cold" && inventory.clothing < 5 {
            healthDelta -= 3 * days
        }

        if Double.random(in: 0...1) < 0.20 {
            healthDelta -= Int.random(in: 2...8)
            moraleDelta -= Int.random(in: 1...5)
        }

        party.health = clamp(party.health + healthDelta, lo: 0, hi: 100)
        party.morale = clamp(party.morale + moraleDelta, lo: 0, hi: 100)
    }

    private func checkStarvation() {
        guard inventory.food <= 0 else { return }

        inventory.food = 0
        party.health = clamp(party.health - 25, lo: 0, hi: 100)
        party.morale = clamp(party.morale - 15, lo: 0, hi: 100)
        log("Food is gone. The party weakens from starvation.")
    }

    private func baseEventRisk() -> Double {
        var risk = 0.10
        if pace == .grueling { risk += 0.06 }
        if rations == .bare { risk += 0.04 }
        if party.morale < 45 { risk += 0.05 }
        if party.health < 50 { risk += 0.05 }
        return risk * profession.riskModifier
    }

    private func maybeRandomEvents() {
        maybeWagonBreak()
        maybeDisease()
        maybeBadWeather()
        maybeRobberyOrAnimals()
    }

    private func maybeWagonBreak() {
        var chance = pace == .grueling ? 0.13 : 0.07
        chance *= profession.riskModifier
        guard Double.random(in: 0...1) < chance else { return }

        if inventory.spareParts > 0 {
            inventory.spareParts -= 1
            party.morale = clamp(party.morale + 2, lo: 0, hi: 100)
            log("Wagon breakdown repaired quickly using a spare part.")
            return
        }

        let delay = Int.random(in: 1...3)
        advanceDays(delay)
        party.health = clamp(party.health - (7 * delay), lo: 0, hi: 100)
        party.morale = clamp(party.morale - (5 * delay), lo: 0, hi: 100)
        log("Wagon breakdown caused a \(delay)-day delay.")
    }

    private func maybeDisease() {
        let chance = 0.05 + baseEventRisk()
        guard Double.random(in: 0...1) < chance else { return }

        let diseases: [(String, Int)] = [
            ("Dysentery", 18),
            ("Cholera", 24),
            ("Measles", 14),
            ("Typhoid", 20),
            ("Fever", 16)
        ]

        let picked = diseases.randomElement() ?? ("Fever", 16)

        if inventory.medicine > 0 {
            inventory.medicine -= 1
            let recover = Int.random(in: 10...24)
            party.health = clamp(party.health + recover, lo: 0, hi: 100)
            party.morale = clamp(party.morale + 6, lo: 0, hi: 100)
            log("Illness: \(picked.0). Medicine used. Health +\(recover).")
            return
        }

        party.health = clamp(party.health - picked.1, lo: 0, hi: 100)
        party.morale = clamp(party.morale - (picked.1 / 2), lo: 0, hi: 100)
        log("Illness: \(picked.0). Health -\(picked.1).")
    }

    private func maybeBadWeather() {
        var chance = 0.06
        if weather.name == "Cold" || weather.name == "Hot" {
            chance += 0.07
        }
        guard Double.random(in: 0...1) < (chance * profession.riskModifier) else { return }

        let event = ["storm", "heat", "cold_snap"].randomElement() ?? "storm"

        switch event {
        case "storm":
            let lost = min(inventory.food, Int.random(in: 15...70))
            inventory.food -= lost
            party.morale = clamp(party.morale - 8, lo: 0, hi: 100)
            advanceDays(1)
            log("Storm cost 1 day and \(lost) food.")
        case "heat":
            party.health = clamp(party.health - Int.random(in: 6...14), lo: 0, hi: 100)
            party.morale = clamp(party.morale - 6, lo: 0, hi: 100)
            log("Heat wave drained the party.")
        default:
            if inventory.clothing >= 6 {
                party.morale = clamp(party.morale - 2, lo: 0, hi: 100)
                log("Cold snap hit, but clothing protected the party.")
            } else {
                let damage = Int.random(in: 8...18)
                party.health = clamp(party.health - damage, lo: 0, hi: 100)
                party.morale = clamp(party.morale - 10, lo: 0, hi: 100)
                log("Cold snap harmed the party. Health -\(damage).")
            }
        }
    }

    private func maybeRobberyOrAnimals() {
        guard Double.random(in: 0...1) < (0.06 * profession.riskModifier) else { return }

        let event = ["robbery", "wolves"].randomElement() ?? "robbery"

        if event == "robbery" {
            let stolenMoney = min(inventory.money, Int.random(in: 20...90))
            let stolenFood = min(inventory.food, Int.random(in: 20...80))
            inventory.money -= stolenMoney
            inventory.food -= stolenFood
            party.morale = clamp(party.morale - 12, lo: 0, hi: 100)
            log("Thieves struck. Lost $\(stolenMoney) and \(stolenFood) food.")
        } else {
            let ammoLoss = min(inventory.ammo, Int.random(in: 5...20))
            inventory.ammo -= ammoLoss
            let hurt = Int.random(in: 4...12)
            party.health = clamp(party.health - hurt, lo: 0, hi: 100)
            log("Wolves attacked. Lost \(ammoLoss) ammo and health -\(hurt).")
        }
    }

    private func handleLandmark() {
        for (idx, landmark) in landmarks.enumerated() where idx > lastLandmarkIndex {
            guard milesTraveled >= landmark.miles else { break }

            lastLandmarkIndex = idx
            party.morale = clamp(party.morale + 7, lo: 0, hi: 100)
            log("Reached landmark: \(landmark.name).")

            if Double.random(in: 0...1) < 0.25 {
                let found = Int.random(in: 10...45)
                inventory.food += found
                log("Foraged \(found) food near \(landmark.name).")
            }

            if landmark.hasFort {
                pendingFortShop = true
                log("A fort shop is available at \(landmark.name).")
            }
        }
    }

    private func checkEndConditions() {
        if party.health <= 0 {
            party.alive = false
            gameEnded = true

            if inventory.food == 0 {
                deathReason = "starvation"
            } else if party.morale <= 10 {
                deathReason = "exhaustion"
            } else {
                deathReason = "illness"
            }

            log("Your party has perished from \(deathReason).")
            return
        }

        if milesTraveled >= totalMiles {
            gameEnded = true
            victory = true
            log("You made it to Oregon.")
        }
    }

    private func log(_ message: String) {
        eventLog.insert("[\(dateString)] \(message)", at: 0)
    }

    private func clamp(_ x: Int, lo: Int, hi: Int) -> Int {
        max(lo, min(hi, x))
    }
}
