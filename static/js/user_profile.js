document.addEventListener('DOMContentLoaded', function () {
    let ctx;
    if (window.innerWidth < 768) {
        ctx = document.getElementById('portfolioMobilePieChart').getContext('2d');
    }
    else {
        ctx = document.getElementById('portfolioPieChart').getContext('2d');
    }
    const doughnutCenterText = {
        id: 'doughnutCenterText',
        afterDatasetsDraw(chart, args, options) {
            const { ctx, chartArea: { top, bottom, left, right, width, height } } = chart;
            ctx.save();

            const performanceData = options.performanceData || {};
            const profitPercentage = performanceData.total_profit_in_percentage;
            const currentValueColor = profitPercentage < 0 ? 'red' : 'green';

            const textLines = [
                `Vốn: $${parseInt(performanceData.total_investment).toLocaleString('en-US').concat('k VND') || 'N/A'}`,
                `Hiện tại: $${parseInt(performanceData.total_asset).toLocaleString('en-US').concat('k VND') || 'N/A'}`,
                `Lợi nhuận: ${typeof performanceData.profit_percent === 'number' ? performanceData.profit_percent.toFixed(2) : 'N/A'}%`
            ];

            const fontSize = options.fontSize || Math.min(width, height) / 20;
            const fontStyle = options.fontStyle || 'normal';
            const fontFamily = options.fontFamily || 'Segoe UI, sans-serif';
            const defaultFontColor = options.fontColor || '#3498db';

            ctx.font = `${fontStyle} ${fontSize}px ${fontFamily}`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';

            let startY = top + (height / 2) - (textLines.length * fontSize * 1.2 / 2);

            textLines.forEach((line, index) => {
                ctx.fillStyle = defaultFontColor;
                if (index === 1 || index === 2) {
                    ctx.fillStyle = currentValueColor;
                }
                const textY = startY + index * fontSize * 1.2;
                ctx.fillText(line, left + (width / 2), textY);
            });

            ctx.restore();
        }
    };
    const myPieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: chart_labels,
            datasets: [{
                label: 'Tỉ lệ cổ phiếu',
                data: chart_data,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(199, 199, 199, 0.7)',
                    'rgba(100, 205, 100, 0.7)',
                    'rgba(220, 180, 0, 0.7)',
                    'rgba(220, 20, 60, 0.7)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(199, 199, 199, 1)',
                    'rgba(100, 205, 100, 1)',
                    'rgba(220, 180, 0, 1)',
                    'rgba(220, 20, 60, 1)'
                ],
                borderWidth: 1,
                segmentRadius: 10,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutoutPercentage: 50,
            layout: {
                padding: { bottom: 10 }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        fontColor: 'rgba(255,255,255)',
                        fontSize: 14
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.raw !== null) {
                                label += context.raw.toLocaleString('en-US') + ' VND';
                            }
                            return label;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Phân bổ Danh mục Đầu tư',
                    fontSize: 16,
                    fontColor: 'rgba(255,255,255)'
                },
                doughnutCenterText: {
                    performanceData: performance_data,
                    fontColor: '#3498db',
                    fontSize: 13,
                    fontStyle: 'bold',
                    fontFamily: 'Arial, sans-serif'
                }
            },
            onHover: (event, chartElement) => {
                if (chartElement.length) {
                    ctx.canvas.style.cursor = 'pointer';
                } else {
                    ctx.canvas.style.cursor = 'default';
                }
            }
        },
        plugins: [doughnutCenterText]
    });
});

document.addEventListener('DOMContentLoaded', function () {
    let ctx;

    let isMobile = window.innerWidth < 768;
    if (isMobile) {
        ctx = document.getElementById('profitMobileChart').getContext('2d');
    }
    else {
        ctx = document.getElementById('profitChart').getContext('2d');
    }
    const myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: profit_chart_labels,
            datasets: [
                {
                    label: 'Danh mục đầu tư của bạn',
                    data: profit_chart_total_asset,
                    borderColor: 'rgb(20, 255, 32)',
                    fill: false,
                    hidden: false,
                    pointRadius: 0,
                },
                {
                    label: 'Lợi nhuận gửi ngân hàng',
                    data: profit_chart_total_asset_bank,
                    borderColor: 'rgb(204, 62, 35)',
                    fill: false,
                    hidden: true,
                    pointRadius: 0,
                },
                {
                    label: 'Trung bình thị trường chứng khoán',
                    data: profit_chart_total_asset_index,
                    borderColor: 'rgb(255, 99, 132)',
                    fill: false,
                    hidden: true,
                    pointRadius: 0,
                },
                {
                    label: 'Tổng vốn đầu tư',
                    data: profit_chart_total_investment,
                    borderColor: 'rgb(75, 192, 192)',
                    fill: false,
                    hidden: false,
                    pointRadius: 0,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true,
                            sensitivity: 0.00005
                        },
                        mode: 'xy',
                        drag: {
                            enabled: true,
                            backgroundColor: 'rgba(225,225,225,0.3)',
                            borderColor: 'rgba(225,225,225)',
                            borderWidth: 1
                        }
                    },
                    pan: {
                        enabled: true,
                        mode: 'xy'
                    },
                    limits: {
                        y: {min: 'original', max: 'original'},
                        x: {min: 'original', max: 'original'}
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        filter: function(legendItem, data) {
                            // Chỉ hiển thị legend của các dataset không bị ẩn
                            return !data.datasets[legendItem.datasetIndex].hidden;
                        }
                    }
                },
                tooltip: {
                    enabled: true,  // Tắt tooltip mặc định trên mobile
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += (context.parsed.y).toLocaleString('en-US') + 'k VND';
                            }
                            return label;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Lịch sử lợi nhuận (lợi nhuận ước tính: ' + (profit_percentage ? profit_percentage.toFixed(2) : '') + '%/năm)',
                    font: {
                        size: 16
                    },

                }
            },
            layout: {
                padding: 0
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Tháng' // Tiêu đề của trục x
                    },
                    grid: {
                        display: true,
                        color: 'rgba(255,255,255,0.05)' // Màu của lưới trục x
                    },
                    ticks: {
                        maxTicksLimit: 6
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Giá trị (k VND)' // Tiêu đề của trục y
                    },
                    grid: {
                        display: true,
                        color: 'rgba(255,255,255,0.05)' // Màu của lưới trục y
                    },
                    ticks: {
                        maxTicksLimit: 6
                    }
                }
            }
        }
    });

    if (isMobile) {
        const canvas = myChart.canvas;
    
        // Khi người dùng bắt đầu chạm (touchstart)
        canvas.addEventListener('touchstart', function(e) {
            myChart.options.plugins.tooltip.enabled = true;
            myChart.update();
        });
    
        // Khi người dùng thả tay (touchend)
        canvas.addEventListener('touchend', function(e) {
            myChart.options.plugins.tooltip.enabled = false;
            myChart.update();
        });
    }
    // Sự kiện cho nút Reset Zoom
    document.getElementById('resetZoom').addEventListener('click', function() {
        myChart.resetZoom();
    });

    document.getElementById('resetZoomMobile').addEventListener('click', function() {
        myChart.resetZoom();
    });


    const toggleBank = document.getElementById('toggleBank');

    const toggleIndex = document.getElementById('toggleIndex');

    const toggleBankMobile = document.getElementById('toggleBankMobile');

    const toggleIndexMobile = document.getElementById('toggleIndexMobile'); 4
    
    toggleBank.addEventListener('click', toggleBankFunction);

    toggleBankMobile.addEventListener('touchstart', toggleBankFunction);

    toggleIndex.addEventListener('click', toggleIndexFunction);

    toggleIndexMobile.addEventListener('touchstart', toggleIndexFunction);


    function toggleBankFunction() {
        const bankDataset = myChart.data.datasets.find(ds => ds.label === 'Lợi nhuận gửi ngân hàng');
        bankDataset.hidden = !bankDataset.hidden;
        if (!bankDataset.hidden) {
            this.classList.add('selected');
        } else {
            this.classList.remove('selected');
        }
        myChart.update();
    }

    function toggleIndexFunction() {
        const indexDataset = myChart.data.datasets.find(ds => ds.label === 'Trung bình thị trường chứng khoán');
        indexDataset.hidden = !indexDataset.hidden;
        if (!indexDataset.hidden) {
            this.classList.add('selected');
        } else {
            this.classList.remove('selected');
        }
        myChart.update();
    }

    // Mặc định, nếu bạn muốn nút toggle không hiển thị dấu tích (tức là không chọn)
    // Có thể đảm bảo bằng cách xóa class "selected" sau khi khởi tạo
    document.getElementById('toggleBank').classList.remove('selected');
    document.getElementById('toggleIndex').classList.remove('selected');
});

document.addEventListener('DOMContentLoaded', function () {
    // Chỉ áp dụng cho mobile (window.innerWidth < 768)
    if (window.innerWidth < 768) {
        // Chọn tất cả các phần tử có class .slide-left
        const slideElements = document.querySelectorAll('.slide-left');
        
        // Tạo Intersection Observer
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('show');
                    // Ngừng theo dõi sau khi animation được kích hoạt
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 }); // Khi 10% phần tử xuất hiện trong viewport
        
        // Áp dụng observer cho các phần tử
        slideElements.forEach(el => {
            observer.observe(el);
        });
    }
});