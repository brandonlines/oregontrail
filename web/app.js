(() => {
  const MONTHS = ["March", "April", "May", "June", "July", "August", "September", "October", "November"];

  const WEATHER_BY_MONTH = {
    March: ["Cold", 0.85],
    April: ["Cool", 0.95],
    May: ["Mild", 1.05],
    June: ["Warm", 1.1],
    July: ["Hot", 1.05],
    August: ["Hot", 1.0],
    September: ["Mild", 0.95],
    October: ["Cool", 0.9],
    November: ["Cold", 0.8],
  };

  const LANDMARKS = [
    [120, "Kansas River", false],
    [310, "Big Blue River", false],
    [540, "Fort Kearney", true],
    [800, "Chimney Rock", false],
    [1030, "Fort Laramie", true],
    [1280, "Independence Rock", false],
    [1530, "South Pass", false],
    [1770, "Fort Hall", true],
    [2000, "Willamette Valley", false],
  ];

  const DISEASES = [
    ["Dysentery", 18],
    ["Cholera", 24],
    ["Measles", 14],
    ["Typhoid", 20],
    ["Fever", 16],
  ];

  const PRICES = {
    food: 1,
    ammo: 2,
    clothing: 15,
    spare_parts: 25,
    medicine: 40,
  };

  const PROFESSIONS = {
    b: ["Banker", 1200, 0.95],
    c: ["Carpenter", 900, 1.0],
    f: ["Farmer", 700, 1.08],
  };

  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));

  const rngFromSeed = (seed) => {
    if (!seed) return Math.random;
    let h = 2166136261;
    for (let i = 0; i < seed.length; i += 1) {
      h ^= seed.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    let t = h >>> 0;
    return () => {
      t += 0x6d2b79f5;
      let x = t;
      x = Math.imul(x ^ (x >>> 15), x | 1);
      x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  };

  const ri = (state, lo, hi) => Math.floor(state.rand() * (hi - lo + 1)) + lo;
  const pick = (state, arr) => arr[ri(state, 0, arr.length - 1)];

  const setupScreen = document.getElementById("setupScreen");
  const gameScreen = document.getElementById("gameScreen");
  const logBox = document.getElementById("log");
  const statusGrid = document.getElementById("statusGrid");

  const paceSelect = document.getElementById("paceSelect");
  const rationsSelect = document.getElementById("rationsSelect");
  const travelDaysInput = document.getElementById("travelDaysInput");

  const shopItem = document.getElementById("shopItem");
  const shopQty = document.getElementById("shopQty");

  let state = null;

  const month = () => MONTHS[state.monthIndex];
  const weather = () => WEATHER_BY_MONTH[month()];

  const addLog = (text, level = "") => {
    const p = document.createElement("p");
    p.className = `log-entry ${level}`;
    p.textContent = text;
    logBox.prepend(p);
  };

  const gameOver = (reason) => {
    state.party.alive = false;
    addLog(`Your party has perished. Cause: ${reason}.`, "bad");
    addLog("Start a new game to try another trail run.", "warn");
  };

  const checkEndState = () => {
    if (state.party.health <= 0) {
      if (state.inv.food === 0) {
        gameOver("starvation");
      } else if (state.party.morale <= 10) {
        gameOver("exhaustion");
      } else {
        gameOver("illness");
      }
      return;
    }

    if (state.milesTraveled >= state.totalMiles) {
      state.milesTraveled = state.totalMiles;
      const score = computeScore();
      addLog(`You made it to Oregon on ${month()} ${state.day}. Final score: ${score}.`, "ok");
      state.party.alive = false;
    }
  };

  const updateStatus = () => {
    const [wx] = weather();
    const d = {
      Date: `${month()} ${state.day}`,
      Weather: wx,
      Miles: `${state.milesTraveled}/${state.totalMiles}`,
      Health: `${state.party.health}/100`,
      Morale: `${state.party.morale}/100`,
      Money: `$${state.inv.money}`,
      Food: `${state.inv.food} lbs`,
      Ammo: `${state.inv.ammo}`,
      Clothing: `${state.inv.clothing}`,
      Parts: `${state.inv.spare_parts}`,
      Medicine: `${state.inv.medicine}`,
      Pace: state.pace,
      Rations: state.rations,
      Profession: state.professionName,
    };

    statusGrid.innerHTML = "";
    Object.entries(d).forEach(([k, v]) => {
      const item = document.createElement("div");
      item.className = "status-item";
      item.innerHTML = `<strong>${k}</strong><span>${v}</span>`;
      statusGrid.appendChild(item);
    });

    paceSelect.value = state.pace;
    rationsSelect.value = state.rations;
  };

  const advanceDays = (days) => {
    state.day += days;
    while (state.day > 30) {
      state.day -= 30;
      state.monthIndex = Math.min(state.monthIndex + 1, MONTHS.length - 1);
    }
  };

  const foodUsePerDay = () => ({ bare: 6, meager: 10, filling: 14 }[state.rations]);
  const paceMilesPerDay = () => ({ slow: 12, steady: 18, grueling: 26 }[state.pace]);

  const baseEventRisk = () => {
    let risk = 0.1;
    if (state.pace === "grueling") risk += 0.06;
    if (state.rations === "bare") risk += 0.04;
    if (state.party.morale < 45) risk += 0.05;
    if (state.party.health < 50) risk += 0.05;
    return risk * state.riskModifier;
  };

  const applyWear = (days) => {
    let hd = 0;
    let md = 0;

    if (state.rations === "bare") {
      hd -= 5 * days;
      md -= 3 * days;
    } else if (state.rations === "meager") {
      hd -= 2 * days;
      md -= days;
    } else {
      hd += days;
      md += days;
    }

    if (state.pace === "grueling") {
      hd -= 4 * days;
      md -= 2 * days;
    } else if (state.pace === "steady") {
      hd -= days;
    }

    const [wx] = weather();
    if (wx === "Cold" && state.inv.clothing < 5) {
      hd -= 3 * days;
    }

    if (state.rand() < 0.2) {
      hd -= ri(state, 2, 8);
      md -= ri(state, 1, 5);
    }

    state.party.health = clamp(state.party.health + hd, 0, 100);
    state.party.morale = clamp(state.party.morale + md, 0, 100);
  };

  const checkStarvation = () => {
    if (state.inv.food > 0) return;
    state.party.health = clamp(state.party.health - 25, 0, 100);
    state.party.morale = clamp(state.party.morale - 15, 0, 100);
    addLog("Food is gone. Starvation weakens the party.", "bad");
  };

  const maybeDisease = () => {
    if (state.rand() >= 0.05 + baseEventRisk()) return;
    const [name, severity] = pick(state, DISEASES);
    addLog(`Illness strikes: ${name}.`, "warn");

    if (state.inv.medicine > 0) {
      state.inv.medicine -= 1;
      const heal = ri(state, 10, 24);
      state.party.health = clamp(state.party.health + heal, 0, 100);
      state.party.morale = clamp(state.party.morale + 6, 0, 100);
      addLog(`Medicine used automatically. Health +${heal}.`, "ok");
      return;
    }

    state.party.health = clamp(state.party.health - severity, 0, 100);
    state.party.morale = clamp(state.party.morale - Math.floor(severity / 2), 0, 100);
    addLog(`No medicine. Health -${severity}.`, "bad");
  };

  const maybeBreakdown = () => {
    let chance = state.pace === "grueling" ? 0.13 : 0.07;
    chance *= state.riskModifier;
    if (state.rand() >= chance) return;

    addLog("Wagon breakdown.", "warn");
    if (state.inv.spare_parts > 0) {
      state.inv.spare_parts -= 1;
      state.party.morale = clamp(state.party.morale + 2, 0, 100);
      addLog("Used 1 spare part for quick repair.", "ok");
      return;
    }

    const delay = ri(state, 1, 3);
    advanceDays(delay);
    state.party.health = clamp(state.party.health - 7 * delay, 0, 100);
    state.party.morale = clamp(state.party.morale - 5 * delay, 0, 100);
    addLog(`No spare parts. Repairs cost ${delay} day(s).`, "bad");
  };

  const maybeWeatherEvent = () => {
    const [wx] = weather();
    let chance = 0.06;
    if (wx === "Cold" || wx === "Hot") chance += 0.07;
    if (state.rand() >= chance * state.riskModifier) return;

    const ev = pick(state, ["storm", "heat", "cold"]);
    if (ev === "storm") {
      const lost = Math.min(state.inv.food, ri(state, 15, 70));
      state.inv.food -= lost;
      state.party.morale = clamp(state.party.morale - 8, 0, 100);
      advanceDays(1);
      addLog(`Storm damage: -${lost} food and +1 day delay.`, "warn");
    } else if (ev === "heat") {
      const dmg = ri(state, 6, 14);
      state.party.health = clamp(state.party.health - dmg, 0, 100);
      state.party.morale = clamp(state.party.morale - 6, 0, 100);
      addLog(`Heat wave drains the party (Health -${dmg}).`, "warn");
    } else if (state.inv.clothing >= 6) {
      state.party.morale = clamp(state.party.morale - 2, 0, 100);
      addLog("Cold snap, but clothing protects the party.", "ok");
    } else {
      const dmg = ri(state, 8, 18);
      state.party.health = clamp(state.party.health - dmg, 0, 100);
      state.party.morale = clamp(state.party.morale - 10, 0, 100);
      addLog(`Cold snap harms the party (Health -${dmg}).`, "bad");
    }
  };

  const maybeRaid = () => {
    if (state.rand() >= 0.06 * state.riskModifier) return;
    if (state.rand() < 0.5) {
      const stolenMoney = Math.min(state.inv.money, ri(state, 20, 90));
      const stolenFood = Math.min(state.inv.food, ri(state, 20, 80));
      state.inv.money -= stolenMoney;
      state.inv.food -= stolenFood;
      state.party.morale = clamp(state.party.morale - 12, 0, 100);
      addLog(`Thieves steal $${stolenMoney} and ${stolenFood} food.`, "bad");
    } else {
      const ammoLoss = Math.min(state.inv.ammo, ri(state, 5, 20));
      const hurt = ri(state, 4, 12);
      state.inv.ammo -= ammoLoss;
      state.party.health = clamp(state.party.health - hurt, 0, 100);
      addLog(`Wolf attack! -${ammoLoss} ammo and Health -${hurt}.`, "warn");
    }
  };

  const maybeRiver = () => {
    const progress = state.milesTraveled / state.totalMiles;
    const chance = progress < 0.8 ? 0.1 : 0.05;
    if (state.rand() >= chance) return;

    const depth = ri(state, 2, 8);
    const strategy = depth >= 6 && state.inv.money >= 40 ? "ferry" : depth >= 5 ? "caulk" : "ford";

    if (strategy === "ferry") {
      state.inv.money -= 40;
      addLog(`Deep river (${depth} ft). Paid ferry fee $40 for a safe crossing.`, "ok");
      return;
    }

    const risk = strategy === "ford" ? 0.1 + 0.05 * (depth - 2) : 0.08 + 0.03 * (depth - 2);
    if (strategy === "caulk") {
      advanceDays(1);
    }

    if (state.rand() < risk * state.riskModifier) {
      const lostFood = Math.min(state.inv.food, ri(state, 35, 130));
      const lostAmmo = Math.min(state.inv.ammo, ri(state, 5, 25));
      const dmg = ri(state, 8, 24);
      state.inv.food -= lostFood;
      state.inv.ammo -= lostAmmo;
      state.party.health = clamp(state.party.health - dmg, 0, 100);
      state.party.morale = clamp(state.party.morale - 10, 0, 100);
      addLog(`River disaster (${depth} ft): -${lostFood} food, -${lostAmmo} ammo, Health -${dmg}.`, "bad");
    } else {
      addLog(`River crossing (${depth} ft) succeeded via ${strategy}.`, "ok");
    }
  };

  const maybeLandmark = () => {
    for (let i = state.lastLandmarkIndex + 1; i < LANDMARKS.length; i += 1) {
      const [miles, name, fort] = LANDMARKS[i];
      if (state.milesTraveled < miles) break;
      state.lastLandmarkIndex = i;
      state.party.morale = clamp(state.party.morale + 7, 0, 100);
      addLog(`Landmark reached: ${name} (${miles} miles).`, "ok");

      if (state.rand() < 0.25) {
        const found = ri(state, 10, 45);
        state.inv.food += found;
        addLog(`Foraging success near ${name}: +${found} food.`, "ok");
      }

      if (fort) {
        addLog(`${name} has a fort. You can use Shop freely this turn.`, "warn");
        state.fortOpen = true;
      }
    }
  };

  const computeScore = () => {
    const bonus = { b: 0.8, c: 1.0, f: 1.25 }[state.professionKey];
    const base = state.party.health + state.party.morale;
    const supplies = Math.floor(state.inv.food / 5) + Math.floor(state.inv.money / 10) + state.inv.medicine * 10;
    return Math.floor((base + supplies) * bonus);
  };

  const runTurn = (days) => {
    if (!state.party.alive) return;

    state.fortOpen = false;
    state.inv.food = Math.max(0, state.inv.food - foodUsePerDay() * days);
    advanceDays(days);

    const [, wxFactor] = weather();
    const miles = Math.floor(paceMilesPerDay() * wxFactor * days);
    state.milesTraveled = Math.min(state.totalMiles, state.milesTraveled + miles);
    addLog(`Traveled ${miles} miles over ${days} day(s).`);

    applyWear(days);
    checkStarvation();
    maybeBreakdown();
    maybeDisease();
    maybeWeatherEvent();
    maybeRaid();
    maybeRiver();
    maybeLandmark();
    checkEndState();
    updateStatus();
  };

  const startGame = () => {
    const seed = document.getElementById("seedInput").value.trim();
    const professionKey = document.getElementById("professionSelect").value;
    const [professionName, money, riskModifier] = PROFESSIONS[professionKey];

    const defaultNames = ["You", "Alex", "Sam", "Jordan", "Casey"];
    const names = [1, 2, 3, 4, 5].map((n, i) => {
      const v = document.getElementById(`name${n}`).value.trim();
      return v || defaultNames[i];
    });

    state = {
      rand: rngFromSeed(seed),
      totalMiles: 2000,
      milesTraveled: 0,
      monthIndex: Number(document.getElementById("monthSelect").value),
      day: 1,
      party: {
        names,
        health: 100,
        morale: 75,
        alive: true,
      },
      inv: {
        money,
        food: 250,
        ammo: 30,
        clothing: 4,
        spare_parts: 1,
        medicine: 0,
      },
      professionKey,
      professionName,
      riskModifier,
      pace: "steady",
      rations: "meager",
      lastLandmarkIndex: -1,
      fortOpen: false,
    };

    setupScreen.classList.add("hidden");
    gameScreen.classList.remove("hidden");
    logBox.innerHTML = "";

    addLog(`Party formed: ${state.party.names.join(", ")}.`, "ok");
    addLog(`You depart in ${month()} as a ${professionName}.`, "ok");
    addLog("Tip: buy supplies before long grueling pushes.");
    updateStatus();
  };

  document.getElementById("startBtn").addEventListener("click", startGame);

  document.getElementById("travelBtn").addEventListener("click", () => {
    if (!state || !state.party.alive) return;
    state.pace = paceSelect.value;
    state.rations = rationsSelect.value;

    const days = clamp(Number(travelDaysInput.value) || 7, 3, 14);
    travelDaysInput.value = String(days);
    runTurn(days);
  });

  document.getElementById("huntBtn").addEventListener("click", () => {
    if (!state || !state.party.alive) return;
    if (state.inv.ammo <= 0) {
      addLog("No ammo available for hunting.", "warn");
      return;
    }

    const spend = Math.min(state.inv.ammo, ri(state, 5, 14));
    state.inv.ammo -= spend;

    const success = state.rand() < 0.7;
    if (!success) {
      state.party.morale = clamp(state.party.morale - 4, 0, 100);
      addLog(`Hunt failed. Ammo spent: ${spend}.`, "warn");
      updateStatus();
      return;
    }

    const gain = ri(state, 80, 220);
    const cap = 1000;
    const actual = Math.max(0, Math.min(cap, state.inv.food + gain) - state.inv.food);
    state.inv.food += actual;
    state.party.morale = clamp(state.party.morale + 6, 0, 100);
    addLog(`Successful hunt. Ammo -${spend}, food +${actual}.`, "ok");
    updateStatus();
  });

  document.getElementById("restBtn").addEventListener("click", () => {
    if (!state || !state.party.alive) return;
    const days = 2;
    advanceDays(days);
    state.inv.food = Math.max(0, state.inv.food - foodUsePerDay() * days);
    state.party.health = clamp(state.party.health + 4 * days, 0, 100);
    state.party.morale = clamp(state.party.morale + 5 * days, 0, 100);
    checkStarvation();
    addLog(`Rested ${days} day(s): health and morale improved.`, "ok");
    checkEndState();
    updateStatus();
  });

  document.getElementById("shopBtn").addEventListener("click", () => {
    if (!state || !state.party.alive) return;
    if (!state.fortOpen && state.rand() >= 0.35) {
      addLog("No town or fort trading post nearby right now.", "warn");
      return;
    }
    addLog("Trading post found. Use the Store section below.", "ok");
  });

  document.getElementById("buyBtn").addEventListener("click", () => {
    if (!state || !state.party.alive) return;
    const item = shopItem.value;
    const qty = Math.max(1, Number(shopQty.value) || 1);
    const cost = qty * PRICES[item];

    if (state.inv.money < cost) {
      addLog(`Cannot afford ${qty} ${item}. Need $${cost}.`, "warn");
      return;
    }

    state.inv.money -= cost;
    state.inv[item] += qty;
    addLog(`Purchased ${qty} ${item} for $${cost}.`, "ok");
    updateStatus();
  });

  document.getElementById("newGameBtn").addEventListener("click", () => {
    gameScreen.classList.add("hidden");
    setupScreen.classList.remove("hidden");
  });
})();
