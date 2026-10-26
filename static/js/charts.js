(function () {
    "use strict";

    if (typeof Chart === "undefined") {
        return;
    }

    var fontFamily = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    Chart.defaults.font.family = fontFamily;
    Chart.defaults.color = "#69736e";
    Chart.defaults.borderColor = "#e5e8e3";

    var palette = [
        "#0e6b4b",
        "#3d8a69",
        "#6aa88c",
        "#94c1ab",
        "#b9d3c5",
        "#ccd6d0",
        "#aeb8b1",
        "#8f9a93",
        "#d8ddd9",
        "#e4e7e3"
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

    var tooltipStyles = {
        backgroundColor: "#18211d",
        titleColor: "#f4f6f4",
        bodyColor: "#d9dfdb",
        borderColor: "rgba(255, 255, 255, 0.08)",
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        titleFont: {
            weight: "600",
            size: 12
        },
        bodyFont: {
            size: 12
        }
    };

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
                        backgroundColor: "#0e6b4b",
                        hoverBackgroundColor: "#0a573c",
                        borderRadius: 6,
                        borderSkipped: false,
                        maxBarThickness: 34,
                        categoryPercentage: 0.72,
                        barPercentage: 0.86
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: reducedMotion ? false : { duration: 500 },
                interaction: {
                    intersect: false,
                    mode: "index"
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        ...tooltipStyles,
                        displayColors: false,
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
                            display: false,
                            drawBorder: false
                        },
                        border: {
                            display: false
                        },
                        ticks: {
                            color: "#69726c",
                            font: {
                                size: 11
                            },
                            maxRotation: 0
                        }
                    },
                    y: {
                        beginAtZero: true,
                        border: {
                            display: false
                        },
                        grid: {
                            color: "#eef0ec",
                            drawTicks: false
                        },
                        ticks: {
                            color: "#69726c",
                            font: {
                                size: 11
                            },
                            maxTicksLimit: 5,
                            padding: 8,
                            callback: function (value) {
                                return Number(value).toLocaleString();
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
            return palette[index % palette.length];
        });

        new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: data.labels,
                datasets: [
                    {
                        data: data.values,
                        backgroundColor: colors,
                        hoverBackgroundColor: colors,
                        borderColor: "#ffffff",
                        borderWidth: 3,
                        hoverOffset: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: reducedMotion ? false : { duration: 500 },
                cutout: "66%",
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        ...tooltipStyles,
                        callbacks: {
                            label: function (context) {
                                return context.label + " · " + formatAmount(data.currency, context.parsed);
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
