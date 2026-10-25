(function () {
    "use strict";

    var shell = document.querySelector(".app-shell");
    var toggle = document.getElementById("sidebar-toggle");

    if (!shell || !toggle) {
        return;
    }

    var storageKey = "expense-tracker:sidebar-collapsed";

    function apply(collapsed, persist) {
        document.body.classList.toggle("sidebar-collapsed", collapsed);
        toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");

        var label = collapsed ? "Expand sidebar" : "Collapse sidebar";
        toggle.setAttribute("aria-label", label);
        toggle.setAttribute("title", label);

        if (persist) {
            try {
                window.localStorage.setItem(storageKey, collapsed ? "1" : "0");
            } catch (error) {
                /* Storage can be unavailable; collapsing still works. */
            }
        }
    }

    var collapsed = false;
    try {
        collapsed = window.localStorage.getItem(storageKey) === "1";
    } catch (error) {
        collapsed = false;
    }

    apply(collapsed, false);

    toggle.addEventListener("click", function () {
        apply(!document.body.classList.contains("sidebar-collapsed"), true);
    });
})();
