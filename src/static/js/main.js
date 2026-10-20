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
  const circumference = 2 * Math.PI * 102;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const values = { sex: 0, chol: 1, glucose: 1, smoke: 0 };

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
    gaugeDescription.textContent = `${probabilityPercent.toFixed(1)} percent estimated risk; ${result.risk_tier} tier.`;
    tierBadge.className = `tier-badge ${tierClass(result.risk_tier)}`;
    tierText.textContent = `${result.risk_tier.toUpperCase()} RISK`;
    mapValueElement.textContent = Number(result.map_value).toFixed(1);
    adviceElement.textContent = result.clinical_advice;
    statusElement.textContent = "Assessment updated successfully.";
    statusElement.classList.remove("error");
  }

  async function requestPrediction() {
    const systolic = Number(systolicInput.value);
    const diastolic = Number(diastolicInput.value);
    if (diastolic >= systolic) {
      statusElement.textContent = "Please ensure diastolic pressure is lower than systolic pressure.";
      statusElement.classList.add("error");
      return;
    }

    statusElement.textContent = "Analyzing clinical parameters…";
    statusElement.classList.remove("error");
    try {
      const response = await fetch("/api/predict", {
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
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Prediction request failed.");
      renderPrediction(result);
    } catch (error) {
      statusElement.textContent = error.message || "Unable to contact the prediction service.";
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
