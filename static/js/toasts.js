(function () {
    "use strict";

    const container = document.querySelector("[data-app-toasts]");
    if (!container || !window.bootstrap) {
        return;
    }

    container.querySelectorAll(".toast").forEach(function (toastElement) {
        const progressBar = toastElement.querySelector(
            ".app-toast-progress-bar"
        );
        const delay =
            Number(toastElement.getAttribute("data-bs-delay")) || 5000;

        if (progressBar) {
            progressBar.style.animationDuration = delay + "ms";

            toastElement.addEventListener("mouseleave", function () {
                progressBar.style.animation = "none";
                void progressBar.offsetWidth;
                progressBar.style.animation = "";
                progressBar.style.animationDuration = delay + "ms";
            });
        }

        bootstrap.Toast.getOrCreateInstance(toastElement).show();
    });
})();
