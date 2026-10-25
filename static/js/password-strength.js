(function () {
    "use strict";

    var input = document.getElementById("id_password1");
    var container = document.querySelector("[data-password-strength]");

    if (!input || !container) {
        return;
    }

    var fill = container.querySelector("[data-password-strength-fill]");
    var progress = container.querySelector("[role='progressbar']");
    var label = container.querySelector("[data-password-strength-label]");
    var hint = container.querySelector("[data-password-strength-hint]");

    var levels = [
        {
            label: "",
            hint: "Use at least 8 characters.",
            color: "",
            width: 0,
            valueText: "No password entered"
        },
        {
            label: "Very weak",
            hint: "Use at least 8 characters.",
            color: "bg-danger",
            width: 20,
            valueText: "Very weak"
        },
        {
            label: "Weak",
            hint: "Mix upper and lowercase letters.",
            color: "bg-danger",
            width: 40,
            valueText: "Weak"
        },
        {
            label: "Fair",
            hint: "Add numbers or symbols to improve it.",
            color: "bg-warning",
            width: 60,
            valueText: "Fair"
        },
        {
            label: "Good",
            hint: "Good enough. Add a symbol or more length for strong.",
            color: "bg-success",
            width: 80,
            valueText: "Good"
        },
        {
            label: "Strong",
            hint: "Strong password. You are good to go.",
            color: "bg-success",
            width: 100,
            valueText: "Strong"
        }
    ];

    function score(value) {
        if (!value) {
            return 0;
        }

        var variety = 0;
        if (/[a-z]/.test(value)) {
            variety += 1;
        }
        if (/[A-Z]/.test(value)) {
            variety += 1;
        }
        if (/\d/.test(value)) {
            variety += 1;
        }
        if (/[^A-Za-z0-9]/.test(value)) {
            variety += 1;
        }

        var total = 0;
        if (value.length >= 8) {
            total += 2;
        }
        if (variety >= 2) {
            total += 1;
        }
        if (variety >= 3) {
            total += 1;
        }
        if (variety >= 4) {
            total += 1;
        }
        if (value.length >= 12) {
            total += 1;
        }

        if (value.length < 8 || variety === 1) {
            total = Math.min(total, 2);
        }

        return Math.min(total, 5);
    }

    function update() {
        var level = score(input.value);
        var state = levels[level];
        var colorClasses = ["bg-danger", "bg-warning", "bg-success"];

        fill.style.width = state.width + "%";
        fill.classList.remove.apply(fill.classList, colorClasses);
        if (state.color) {
            fill.classList.add(state.color);
        }

        label.textContent = state.label;
        hint.textContent = state.hint;

        progress.setAttribute("aria-valuenow", String(level));
        progress.setAttribute("aria-valuetext", state.valueText);
    }

    input.addEventListener("input", update);
    update();
})();
