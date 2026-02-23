import Foundation

enum Pace: String, CaseIterable, Identifiable {
    case slow
    case steady
    case grueling

    var id: String { rawValue }

    var milesPerDay: Int {
        switch self {
        case .slow: return 12
        case .steady: return 18
        case .grueling: return 26
        }
    }
}

enum Rations: String, CaseIterable, Identifiable {
    case bare
    case meager
    case filling

    var id: String { rawValue }

    var foodPerDay: Int {
        switch self {
        case .bare: return 6
        case .meager: return 10
        case .filling: return 14
        }
    }
}

struct Profession: Identifiable, Equatable {
    let key: String
    let name: String
    let startingMoney: Int
    let riskModifier: Double
    let scoreBonus: Double

    var id: String { key }

    static let banker = Profession(key: "b", name: "Banker", startingMoney: 1200, riskModifier: 0.95, scoreBonus: 0.8)
    static let carpenter = Profession(key: "c", name: "Carpenter", startingMoney: 900, riskModifier: 1.0, scoreBonus: 1.0)
    static let farmer = Profession(key: "f", name: "Farmer", startingMoney: 700, riskModifier: 1.08, scoreBonus: 1.25)

    static let all = [banker, carpenter, farmer]
}

struct Weather {
    let name: String
    let milesFactor: Double
}

struct Landmark: Identifiable {
    let miles: Int
    let name: String
    let hasFort: Bool

    var id: String { "\(miles)-\(name)" }
}

struct Party {
    var names: [String] = ["You", "Alex", "Sam", "Jordan", "Casey"]
    var health: Int = 100
    var morale: Int = 75
    var alive: Bool = true
}

struct Inventory {
    var money: Int = 0
    var food: Int = 0
    var ammo: Int = 0
    var clothing: Int = 0
    var spareParts: Int = 0
    var medicine: Int = 0
}

struct PriceList {
    static let food = 1
    static let ammo = 2
    static let clothing = 15
    static let spareParts = 25
    static let medicine = 40
}

enum ShopItem: String, CaseIterable, Identifiable {
    case food
    case ammo
    case clothing
    case spareParts
    case medicine

    var id: String { rawValue }

    var price: Int {
        switch self {
        case .food: return PriceList.food
        case .ammo: return PriceList.ammo
        case .clothing: return PriceList.clothing
        case .spareParts: return PriceList.spareParts
        case .medicine: return PriceList.medicine
        }
    }

    var title: String {
        switch self {
        case .food: return "Food"
        case .ammo: return "Ammo"
        case .clothing: return "Clothing"
        case .spareParts: return "Spare Parts"
        case .medicine: return "Medicine"
        }
    }
}
