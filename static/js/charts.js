(function () {
    "use strict";

    if (typeof Chart === "undefined") {
        return;
    }

    var palette = [
        "#146c43",
        "#198754",
        "#20c997",
        "#0d6efd",
        "#6f42c1",
        "#fd7e14",
        "#dc3545",
        "#6c757d",
        "#0dcaf0",
        "#ffc107"
    ];

    function readData(elementId) {
        var element = document.getElementById(elementId);
        if (!element) {
            return null;
        }

        try {
            return JSON.parse(element.textContent);
        } catch (error) {
            return null;
        }
    }

    function formatAmount(currency, value) {
        return currency + " " + Number(value).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function buildTrendChart() {
        var canvas = document.getElementById("monthly-trend-chart");
        var data = readData("monthly-trend-data");
        if (!canvas || !data || !data.values.length) {
            return;
        }

        new Chart(canvas, {
            type: "bar",
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: "Expenses",
                        data: data.values,
                        backgroundColor: "#146c43",
                        borderRadius: 4,
                        maxBarThickness: 42
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return formatAmount(data.currency, context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return data.currency + " " + Number(value).toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    function buildCategoryChart() {
        var canvas = document.getElementById("category-spending-chart");
        var data = readData("category-spending-data");
        if (!canvas || !data || !data.values.length) {
            return;
        }

        var colors = data.labels.map(function (label, index) {
            if (index < palette.length) {
                return palette[index];
            }
            return "hsl(" + ((index * 47) % 360) + " 55% 45%)";
        });

        new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: data.labels,
                datasets: [
                    {
                        data: data.values,
                        backgroundColor: colors,
                        borderColor: "#ffffff",
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "58%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            boxWidth: 12,
                            padding: 12,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return context.label + ": " + formatAmount(data.currency, context.parsed);
                            }
                        }
                    }
                }
            }
        });
    }

    buildTrendChart();
    buildCategoryChart();
})();
