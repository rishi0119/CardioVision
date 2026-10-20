(() => {
  "use strict";

  const canvas = document.getElementById("particle-canvas");
  const context = canvas.getContext("2d", { alpha: true });
  const form = document.getElementById("patient-form");
  const statusElement = document.getElementById("request-status");
  const gaugeProgress = document.getElementById("gauge-progress");
  const gaugeNumber = document.getElementById("gauge-number");
  const gaugeDescription = document.getElementById("gauge-desc");
  const tierBadge = document.getElementById("tier-badge");
  const tierText = document.getElementById("tier-text");
  const mapValueElement = document.getElementById("map-value");
  const adviceElement = document.getElementById("clinical-advice");
  const ageInput = document.getElementById("age");
  const systolicInput = document.getElementById("sysBP");
  const diastolicInput = document.getElementById("diaBP");
  const bpWarning = document.getElementById("bp-warning");
  const translations = window.CARDIO_TRANSLATIONS;
  const languageSelect = document.getElementById("language-select");
  const authDialog = document.getElementById("auth-dialog");
  const authForm = document.getElementById("auth-form");
  const authStatus = document.getElementById("auth-status");
  const historyDialog = document.getElementById("history-dialog");
  const historyBody = document.getElementById("history-body");
  const historyStatus = document.getElementById("history-status");
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  let language = "en";
  let authMode = "login";
  let signedInUser = null;
  const circumference = 2 * Math.PI * 102;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const values = { sex: 0, chol: 1, glucose: 1, smoke: 0 };

  function text(key) {
    return translations[language][key] || translations.en[key] || key;
  }

  function translatePage() {
    document.documentElement.lang = language;
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = text(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
      element.setAttribute("aria-label", text(element.dataset.i18nAria));
    });
    languageSelect.value = language;
    updateAuthMode();
    if (signedInUser) updateAccountNavigation();
  }

  function translatedTier(tier) {
    const key = { Low: "tierLow", Moderate: "tierModerate", High: "tierHigh", Critical: "tierCritical" }[tier];
    return key ? text(key) : tier;
  }

  function translatedAdvice(advice) {
    const adviceKeys = {
      "Continue routine preventive care and monitoring.": "adviceRoutine",
      "Review the overall risk profile with a healthcare professional.": "adviceModerate",
      "Consider timely clinical review of cardiovascular risk factors.": "adviceHigh",
      "Prompt professional assessment is appropriate; this estimate is not a diagnosis.": "adviceCritical",
      "Blood pressure is markedly elevated; seek prompt professional assessment.": "adviceBp",
      "Discuss this risk estimate promptly with a qualified healthcare professional.": "adviceDiscuss",
      "Monitor blood pressure closely and discuss the reading with a healthcare professional.": "adviceMapHigh",
      "MAP is on the lower side; interpret with symptoms and seek clinical advice if concerned.": "adviceMapLow",
      "Consider timely clinical review and ongoing monitoring of cardiovascular risk factors.": "adviceHighReview",
      "Review preventive health goals and maintain regular follow-up.": "adviceModerateReview",
      "Continue routine preventive care and periodic blood-pressure monitoring.": "adviceRoutineReview",
    };
    return adviceKeys[advice] ? text(adviceKeys[advice]) : advice;
  }

  function updateAuthMode() {
    const registerMode = authMode === "register";
    document.getElementById("auth-title").textContent = text(registerMode ? "navRegister" : "navLogin");
    document.getElementById("auth-submit").textContent = text(registerMode ? "navRegister" : "navLogin");
    document.getElementById("username-field").hidden = !registerMode;
    document.getElementById("auth-username").required = registerMode;
    document.getElementById("auth-password").autocomplete = registerMode ? "new-password" : "current-password";
    document.querySelectorAll("[data-auth-mode]").forEach((button) => {
      const active = button.dataset.authMode === authMode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
  }

  function updateAccountNavigation() {
    const authenticated = Boolean(signedInUser);
    document.getElementById("welcome-message").hidden = !authenticated;
    document.getElementById("welcome-message").textContent = authenticated
      ? text("welcome").replace("{username}", signedInUser.username)
      : "";
    document.getElementById("history-button").hidden = !authenticated;
    document.getElementById("login-button").hidden = authenticated;
    document.getElementById("register-button").hidden = authenticated;
    document.getElementById("logout-button").hidden = !authenticated;
  }

  async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        "X-CSRFToken": csrfToken,
      },
    });
    let result;
    try {
      result = await response.json();
    } catch {
      throw new Error(text("requestFailed"));
    }
    if (!response.ok) {
      if (result.error === "authentication_required") {
        signedInUser = null;
        updateAccountNavigation();
      }
      throw new Error(result.message || result.error || text("requestFailed"));
    }
    return result;
  }

  function openAuth(mode) {
    authMode = mode;
    authStatus.textContent = "";
    updateAuthMode();
    authDialog.showModal();
  }

  function renderHistory(records) {
    historyBody.replaceChildren();
    if (!records.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 6;
      cell.textContent = text("noHistory");
      row.appendChild(cell);
      historyBody.appendChild(row);
      return;
    }

    const locale = { en: "en", te: "te-IN", hi: "hi-IN" }[language];
    const dateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });
    records.forEach((record) => {
      const row = document.createElement("tr");
      const date = new Date(record.created_at);
      const tier = record.risk_tier;
      const cells = [
        dateFormatter.format(date),
        String(record.age),
        `${record.sys_bp}/${record.dia_bp} mmHg`,
        Number(record.map_val).toFixed(1),
        `${(record.risk_probability * 100).toFixed(1)}%`,
      ];
      cells.forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      const tierCell = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = `history-tier tier-${tier.toLowerCase()}`;
      badge.textContent = translatedTier(tier);
      tierCell.appendChild(badge);
      row.appendChild(tierCell);
      historyBody.appendChild(row);
    });
  }

  async function loadHistory() {
    historyStatus.textContent = text("loadingHistory");
    try {
      const result = await apiRequest("/api/history");
      renderHistory(result.history);
      historyStatus.textContent = "";
    } catch (error) {
      historyStatus.textContent = error.message === "authentication_required" ? text("navLogin") : text("historyFailed");
      historyBody.replaceChildren();
    }
  }

  languageSelect.addEventListener("change", () => {
    language = languageSelect.value;
    translatePage();
  });
  translatePage();
  updateAccountNavigation();

  document.getElementById("login-button").addEventListener("click", () => openAuth("login"));
  document.getElementById("register-button").addEventListener("click", () => openAuth("register"));
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      authMode = button.dataset.authMode;
      authStatus.textContent = "";
      updateAuthMode();
    });
  });
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => document.getElementById(button.dataset.closeDialog).close());
  });
  [authDialog, historyDialog].forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });

  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    authStatus.textContent = "";
    const formData = new FormData(authForm);
    const payload = {
      email: formData.get("email"),
      password: formData.get("password"),
    };
    if (authMode === "register") payload.username = formData.get("username");
    try {
      const result = await apiRequest(`/api/${authMode === "register" ? "register" : "login"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      signedInUser = result.user;
      updateAccountNavigation();
      authDialog.close();
      authForm.reset();
    } catch (error) {
      authStatus.textContent = error.message;
      authStatus.classList.add("error");
    }
  });

  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      await apiRequest("/api/logout", { method: "POST" });
      signedInUser = null;
      updateAccountNavigation();
    } catch (error) {
      statusElement.textContent = error.message;
      statusElement.classList.add("error");
    }
  });

  document.getElementById("history-button").addEventListener("click", () => {
    historyDialog.showModal();
    loadHistory();
  });

  apiRequest("/api/user").then((result) => {
    signedInUser = result.authenticated ? result.user : null;
    updateAccountNavigation();
  }).catch(() => {
    signedInUser = null;
    updateAccountNavigation();
  });

  gaugeProgress.style.strokeDasharray = String(circumference);
  gaugeProgress.style.strokeDashoffset = String(circumference);

  function updateRangeFill(input) {
    const percent = ((Number(input.value) - Number(input.min)) / (Number(input.max) - Number(input.min))) * 100;
    input.style.background = `linear-gradient(90deg, #00f0ff 0%, #0072ff ${percent * 0.5}%, rgba(104,128,158,.25) ${percent}%)`;
  }

  function updateInputReadouts() {
    document.getElementById("age-value").textContent = ageInput.value;
    document.getElementById("sysBP-value").innerHTML = `${systolicInput.value} <small>mmHg</small>`;
    document.getElementById("diaBP-value").innerHTML = `${diastolicInput.value} <small>mmHg</small>`;
    [ageInput, systolicInput, diastolicInput].forEach(updateRangeFill);
    const invalidPressure = Number(diastolicInput.value) >= Number(systolicInput.value);
    bpWarning.hidden = !invalidPressure;
  }

  [ageInput, systolicInput, diastolicInput].forEach((input) => {
    input.addEventListener("input", updateInputReadouts);
  });
  updateInputReadouts();

  document.querySelectorAll("[data-group]").forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.dataset.group;
      values[group] = Number(button.dataset.value);
      document.querySelectorAll(`[data-group="${group}"]`).forEach((option) => {
        const selected = option === button;
        option.classList.toggle("active", selected);
        option.setAttribute("aria-pressed", String(selected));
      });
    });
  });

  function tierClass(tier) {
    return `tier-${tier.toLowerCase()}`;
  }

  function renderPrediction(result) {
    const probabilityPercent = Math.max(0, Math.min(100, result.probability * 100));
    const offset = circumference * (1 - probabilityPercent / 100);
    const tierColors = {
      Low: "#00e58a",
      Moderate: "#f6d64a",
      High: "#ff9d45",
      Critical: "#ff4c67",
    };
    const color = tierColors[result.risk_tier] || "#00f0ff";

    gaugeProgress.style.strokeDashoffset = String(offset);
    gaugeProgress.style.stroke = color;
    gaugeNumber.textContent = `${probabilityPercent.toFixed(1)}%`;
    const tier = translatedTier(result.risk_tier);
    gaugeDescription.textContent = text("riskEstimate")
      .replace("{percent}", probabilityPercent.toFixed(1))
      .replace("{tier}", tier);
    tierBadge.className = `tier-badge ${tierClass(result.risk_tier)}`;
    tierText.textContent = `${tier.toLocaleUpperCase()} ${text("riskTier").toLocaleUpperCase()}`;
    mapValueElement.textContent = Number(result.map_value).toFixed(1);
    adviceElement.textContent = translatedAdvice(result.clinical_advice);
    statusElement.textContent = text("predictionDone");
    statusElement.classList.remove("error");
  }

  async function requestPrediction() {
    const systolic = Number(systolicInput.value);
    const diastolic = Number(diastolicInput.value);
    if (diastolic >= systolic) {
      statusElement.textContent = text("bpInvalid");
      statusElement.classList.add("error");
      return;
    }

    statusElement.textContent = text("analyzing");
    statusElement.classList.remove("error");
    try {
      const result = await apiRequest("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          age_years: Number(ageInput.value),
          sex: values.sex,
          sysBP: systolic,
          diaBP: diastolic,
          chol: values.chol,
          glucose: values.glucose,
          smoke: values.smoke,
        }),
      });
      renderPrediction(result);
    } catch (error) {
      statusElement.textContent = error.message || text("predictionFailed");
      statusElement.classList.add("error");
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    requestPrediction();
  });

  let width = 0;
  let height = 0;
  let particles = [];
  let frameId = 0;

  function resizeCanvas() {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const count = Math.min(110, Math.max(35, Math.floor((width * height) / 14500)));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.28,
      vy: (Math.random() - 0.5) * 0.28,
      radius: Math.random() * 1.35 + 0.5,
      phase: Math.random() * Math.PI * 2,
    }));
  }

  function animateParticles() {
    context.clearRect(0, 0, width, height);
    const linkDistance = width < 600 ? 95 : 135;
    for (let i = 0; i < particles.length; i += 1) {
      const point = particles[i];
      point.x += point.vx;
      point.y += point.vy;
      point.phase += 0.018;
      if (point.x < -4) point.x = width + 4;
      if (point.x > width + 4) point.x = -4;
      if (point.y < -4) point.y = height + 4;
      if (point.y > height + 4) point.y = -4;

      const glow = 0.46 + (Math.sin(point.phase) + 1) * 0.2;
      context.beginPath();
      context.arc(point.x, point.y, point.radius, 0, Math.PI * 2);
      context.fillStyle = `rgba(0, ${205 + Math.floor(glow * 40)}, 255, ${glow})`;
      context.shadowBlur = 9;
      context.shadowColor = "rgba(0,240,255,.8)";
      context.fill();
      context.shadowBlur = 0;

      for (let j = i + 1; j < particles.length; j += 1) {
        const other = particles[j];
        const dx = point.x - other.x;
        const dy = point.y - other.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < linkDistance) {
          const opacity = (1 - distance / linkDistance) * 0.18;
          context.beginPath();
          context.moveTo(point.x, point.y);
          context.lineTo(other.x, other.y);
          context.strokeStyle = `rgba(0,174,255,${opacity})`;
          context.lineWidth = 0.7;
          context.stroke();
        }
      }
    }
    if (!reducedMotion) frameId = window.requestAnimationFrame(animateParticles);
  }

  window.addEventListener("resize", () => {
    window.cancelAnimationFrame(frameId);
    resizeCanvas();
    animateParticles();
  });
  resizeCanvas();
  animateParticles();
})();
