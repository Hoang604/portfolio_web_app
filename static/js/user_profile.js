document.addEventListener("DOMContentLoaded", function () {
  let ctx = document.getElementById("portfolioPieChart")
    ? document.getElementById("portfolioPieChart").getContext("2d")
    : null;
  if (!ctx) return;

  const doughnutCenterText = {
    id: "doughnutCenterText",
    afterDatasetsDraw(chart, args, options) {
      const {
        ctx,
        chartArea: { top, bottom, left, right, width, height },
      } = chart;
      ctx.save();

      if (options.performanceData.profit_percent != null) {
        options.performanceData.profit_percent = Number(
          options.performanceData.profit_percent,
        );
      }
      const performanceData = options.performanceData || {};
      const profitPercentage = performanceData.profit_percent || 0;
      const currentValueColor = profitPercentage < 0 ? "#dc3545" : "#28a745";

      const formatVNDShort = (val) => {
        if (val == null) return "N/A";
        const v = Number(val);
        if (Math.abs(v) >= 1000000) {
          return (v / 1000000).toFixed(2) + " Tr VNĐ";
        }
        return v.toLocaleString("en-US") + " VNĐ";
      };

      const textLines = [
        `Vốn: ${formatVNDShort(performanceData.total_investment)}`,
        `Hiện tại: ${formatVNDShort(performanceData.total_asset)}`,
        `Lợi nhuận: ${
          typeof profitPercentage === "number"
            ? (profitPercentage >= 0 ? "+" : "") +
              profitPercentage.toFixed(2) +
              "%"
            : "N/A"
        }`,
      ];

      const fontSize = options.fontSize || Math.min(width, height) / 20;
      const fontStyle = options.fontStyle || "bold";
      const fontFamily = options.fontFamily || "Segoe UI, sans-serif";
      const defaultFontColor = options.fontColor || "#3498db";

      ctx.font = `${fontStyle} ${fontSize}px ${fontFamily}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";

      let startY = top + height / 2 - (textLines.length * fontSize * 1.2) / 2;

      textLines.forEach((line, index) => {
        ctx.fillStyle = defaultFontColor;
        if (index === 1 || index === 2) {
          ctx.fillStyle = currentValueColor;
        }
        const textY = startY + index * fontSize * 1.2;
        ctx.fillText(line, left + width / 2, textY);
      });

      ctx.restore();
    },
  };

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: chart_labels,
      datasets: [
        {
          label: "Tỉ lệ cổ phiếu",
          data: chart_data,
          backgroundColor: [
            "rgba(255, 99, 132, 0.7)",
            "rgba(54, 162, 235, 0.7)",
            "rgba(255, 206, 86, 0.7)",
            "rgba(75, 192, 192, 0.7)",
            "rgba(255, 159, 64, 0.7)",
            "rgba(199, 199, 199, 0.7)",
            "rgba(100, 205, 100, 0.7)",
            "rgba(220, 180, 0, 0.7)",
          ],
          borderColor: [
            "rgba(255, 99, 132, 1)",
            "rgba(54, 162, 235, 1)",
            "rgba(255, 206, 86, 1)",
            "rgba(75, 192, 192, 1)",
            "rgba(153, 102, 255, 1)",
            "rgba(255, 159, 64, 1)",
            "rgba(199, 199, 199, 1)",
            "rgba(100, 205, 100, 1)",
          ],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutoutPercentage: 60,
      cutout: "60%",
      plugins: {
        legend: {
          position: "top",
          labels: { color: "#a5b8c9", font: { size: 12 } },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.label || "";
              if (label) label += ": ";
              if (context.raw !== null) {
                label += Number(context.raw).toLocaleString("en-US") + " VNĐ";
              }
              return label;
            },
          },
        },
        doughnutCenterText: {
          performanceData: performance_data,
          fontColor: "#3498db",
          fontSize: 13,
          fontStyle: "bold",
        },
      },
    },
    plugins: [doughnutCenterText],
  });
});

// Profit Line Chart Initialization
document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("profitChartContainer");
  if (!container) return;

  const chart = LightweightCharts.createChart(container, {
    layout: {
      textColor: "#a5b8c9",
      background: { type: "solid", color: "transparent" },
    },
    localization: {
      priceFormatter: function (price) {
        if (Math.abs(price) >= 1000000) {
          return (price / 1000000).toFixed(1) + " Tr";
        }
        return price.toLocaleString("en-US");
      },
    },
    rightPriceScale: {
      visible: true,
      borderColor: "rgba(255,255,255,0.1)",
    },
    leftPriceScale: {
      visible: false,
    },
    grid: {
      vertLines: { color: "rgba(255,255,255,0.05)" },
      horzLines: { color: "rgba(255,255,255,0.05)" },
    },
    timeScale: {
      borderColor: "rgba(255,255,255,0.1)",
      timeVisible: true,
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
    },
  });

  const overlayCanvas = document.getElementById("profitChartOverlay");
  const overlayCtx = overlayCanvas ? overlayCanvas.getContext("2d") : null;

  function syncOverlaySize() {
    if (!overlayCanvas) return;
    const rect = container.getBoundingClientRect();
    overlayCanvas.width = rect.width;
    overlayCanvas.height = rect.height;
    renderOverlay();
  }

  // Handle Resize
  new ResizeObserver((entries) => {
    if (entries.length === 0 || entries[0].target !== container) {
      return;
    }
    const newRect = entries[0].contentRect;
    chart.applyOptions({ height: newRect.height, width: newRect.width });
    syncOverlaySize();
  }).observe(container);

  // Map Data
  const mapData = (labels, values) => {
    return labels.map((dateStr, i) => {
      // Convert "DD/MM/YYYY" to "YYYY-MM-DD"
      const parts = dateStr.split("/");
      let yyyyMmDd = dateStr;
      if (parts.length === 3) {
         yyyyMmDd = `${parts[2]}-${parts[1]}-${parts[0]}`;
      }
      return { time: yyyyMmDd, value: values[i] };
    });
  };

  const assetData = mapData(profit_chart_labels, profit_chart_total_asset);
  const investmentData = mapData(
    profit_chart_labels,
    profit_chart_total_investment,
  );
  const bankData = mapData(profit_chart_labels, profit_chart_total_asset_bank);
  const indexData = mapData(
    profit_chart_labels,
    profit_chart_total_asset_index,
  );

  // Add Series - Line for Asset and the rest
  const assetSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: "rgb(40, 167, 69)",
    lineWidth: 2,
    lineType: LightweightCharts.LineType.Curved,
    title: "Tài sản",
  });
  assetSeries.setData(assetData);

  const investmentSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: "rgb(52, 152, 219)",
    lineWidth: 2,
    lineType: LightweightCharts.LineType.WithSteps,
    title: "Vốn",
  });
  investmentSeries.setData(investmentData);

  const bankSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: "rgb(255, 193, 7)",
    lineWidth: 2,
    title: "Ngân hàng",
    lineType: LightweightCharts.LineType.WithSteps,
    visible: false,
  });
  bankSeries.setData(bankData);

  const indexSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: "rgb(153, 102, 255)",
    lineWidth: 2,
    lineType: LightweightCharts.LineType.Curved,
    title: "VN-INDEX",
    visible: false,
  });
  indexSeries.setData(indexData);

  chart.timeScale().fitContent();

  let animId = null;
  function animateOverlay(duration = 500) {
    if (animId) cancelAnimationFrame(animId);
    const start = performance.now();
    function step(now) {
      renderOverlay();
      if (now - start < duration) {
        animId = requestAnimationFrame(step);
      } else {
        animId = null;
      }
    }
    animId = requestAnimationFrame(step);
  }

  function renderOverlay() {
    if (!overlayCtx || !assetSeries || !investmentSeries) return;
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    
    const logicalRange = chart.timeScale().getVisibleLogicalRange();
    if (!logicalRange) return;

    const fromIndex = Math.max(0, Math.floor(logicalRange.from) - 1);
    const toIndex = Math.min(assetData.length - 1, Math.ceil(logicalRange.to) + 1);

    if (fromIndex >= toIndex) return;

    // TradingView Standard Gradient Fills
    const greenGrad = overlayCtx.createLinearGradient(0, 0, 0, overlayCanvas.height);
    greenGrad.addColorStop(0, "rgba(40, 167, 69, 0.35)");
    greenGrad.addColorStop(1, "rgba(40, 167, 69, 0.02)");

    const redGrad = overlayCtx.createLinearGradient(0, 0, 0, overlayCanvas.height);
    redGrad.addColorStop(0, "rgba(247, 82, 95, 0.02)");
    redGrad.addColorStop(1, "rgba(247, 82, 95, 0.35)");

    overlayCtx.save();
    for (let i = fromIndex; i < toIndex; i++) {
       const d1 = assetData[i];
       const d2 = assetData[i+1];
       const i1 = investmentData[i];
       
       if (!d1 || !d2 || !i1) continue;
       
       const x1 = chart.timeScale().timeToCoordinate(d1.time);
       const x2 = chart.timeScale().timeToCoordinate(d2.time);
       if (x1 === null || x2 === null) continue;

       const ay1 = assetSeries.priceToCoordinate(d1.value);
       const ay2 = assetSeries.priceToCoordinate(d2.value);
       const iy1 = investmentSeries.priceToCoordinate(i1.value);
       
       if (ay1 === null || ay2 === null || iy1 === null) continue;

       let isProfit1 = d1.value >= i1.value;
       let isProfit2 = d2.value >= i1.value;

       if (isProfit1 === isProfit2) {
           overlayCtx.beginPath();
           overlayCtx.moveTo(x1, ay1);
           overlayCtx.lineTo(x2, ay2);
           overlayCtx.lineTo(x2, iy1);
           overlayCtx.lineTo(x1, iy1);
           overlayCtx.closePath();
           overlayCtx.fillStyle = isProfit1 ? greenGrad : redGrad;
           overlayCtx.fill();
       } else {
           const t = (iy1 - ay1) / (ay2 - ay1);
           const crossX = x1 + t * (x2 - x1);
           const crossY = iy1;

           overlayCtx.beginPath();
           overlayCtx.moveTo(x1, ay1);
           overlayCtx.lineTo(crossX, crossY);
           overlayCtx.lineTo(x1, iy1);
           overlayCtx.closePath();
           overlayCtx.fillStyle = isProfit1 ? greenGrad : redGrad;
           overlayCtx.fill();

           overlayCtx.beginPath();
           overlayCtx.moveTo(crossX, crossY);
           overlayCtx.lineTo(x2, ay2);
           overlayCtx.lineTo(x2, iy1);
           overlayCtx.closePath();
           overlayCtx.fillStyle = isProfit2 ? greenGrad : redGrad;
           overlayCtx.fill();
       }
    }
    overlayCtx.restore();
  }

  chart.timeScale().subscribeVisibleTimeRangeChange(renderOverlay);
  chart.subscribeCrosshairMove(renderOverlay);
  
  // Đảm bảo vẽ lần đầu sau khi load data
  setTimeout(() => {
    chart.timeScale().fitContent();
    syncOverlaySize();
    animateOverlay(500);
  }, 100);

  // Reset Zoom
  const btnReset = document.getElementById("resetZoom");
  if (btnReset) {
    btnReset.addEventListener("click", () => {
      chart.timeScale().fitContent();
      animateOverlay(500);
    });
  }

  // Toggles
  const toggleBank = document.getElementById("toggleBank");
  if (toggleBank) {
    toggleBank.addEventListener("click", function () {
      const isVisible = bankSeries.options().visible;
      bankSeries.applyOptions({ visible: !isVisible });
      this.classList.toggle("selected", !isVisible);
      animateOverlay(500);
    });
  }

  const toggleIndex = document.getElementById("toggleIndex");
  if (toggleIndex) {
    toggleIndex.addEventListener("click", function () {
      const isVisible = indexSeries.options().visible;
      indexSeries.applyOptions({ visible: !isVisible });
      this.classList.toggle("selected", !isVisible);
      animateOverlay(500);
    });
  }
});

// Expert Double-Entry Ledger Modal Logic
document.addEventListener("DOMContentLoaded", function () {
  const btnOpenModal = document.getElementById("btnOpenExpertModal");
  const btnCloseModal = document.getElementById("btnCloseExpertModal");
  const modalOverlay = document.getElementById("expertLedgerModal");
  const containerList = document.getElementById("ledgerEntriesList");

  if (!btnOpenModal || !modalOverlay) return;

  btnOpenModal.addEventListener("click", function () {
    modalOverlay.style.display = "flex";
    fetchLedgerData();
  });

  if (btnCloseModal) {
    btnCloseModal.addEventListener("click", function () {
      modalOverlay.style.display = "none";
    });
  }

  modalOverlay.addEventListener("click", function (e) {
    if (e.target === modalOverlay) {
      modalOverlay.style.display = "none";
    }
  });

  let allLedgerEntries = [];
  let currentSelectedCategory = "ALL";

  function fetchLedgerData() {
    containerList.innerHTML =
      '<div class="loading-spinner">Đang tải nhật ký kế toán...</div>';
    const pillsContainer = document.getElementById("ledgerFilterPills");
    if (pillsContainer) pillsContainer.innerHTML = "";

    fetch(`/api/v1/user/${current_user_id}/ledger`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success" && data.journal_entries) {
          allLedgerEntries = data.journal_entries;
          currentSelectedCategory = "ALL";
          renderFilterPills();
          renderFilteredLedgerEntries();
        } else {
          containerList.innerHTML =
            '<div class="error-msg">Không thể tải dữ liệu nhật ký.</div>';
        }
      })
      .catch((err) => {
        console.error(err);
        containerList.innerHTML =
          '<div class="error-msg">Đã xảy ra lỗi khi kết nối API.</div>';
      });
  }

  function renderFilterPills() {
    const pillsContainer = document.getElementById("ledgerFilterPills");
    if (!pillsContainer || allLedgerEntries.length === 0) return;

    // Dynamically extract categories from data
    const categoriesSet = new Set();
    allLedgerEntries.forEach((e) => {
      if (e.category) categoriesSet.add(e.category);
    });

    const categories = Array.from(categoriesSet);

    let pillsHtml = `
      <button class="btn-ledger-pill ${currentSelectedCategory === "ALL" ? "active" : ""}" data-cat="ALL">
        Tất Cả (${allLedgerEntries.length})
      </button>
    `;

    categories.forEach((cat) => {
      const count = allLedgerEntries.filter((e) => e.category === cat).length;
      pillsHtml += `
        <button class="btn-ledger-pill ${currentSelectedCategory === cat ? "active" : ""}" data-cat="${cat}">
          ${cat} (${count})
        </button>
      `;
    });

    pillsContainer.innerHTML = pillsHtml;

    // Bind click events to pills
    pillsContainer.querySelectorAll(".btn-ledger-pill").forEach((btn) => {
      btn.addEventListener("click", function () {
        currentSelectedCategory = this.getAttribute("data-cat");
        pillsContainer
          .querySelectorAll(".btn-ledger-pill")
          .forEach((b) => b.classList.remove("active"));
        this.classList.add("active");
        renderFilteredLedgerEntries();
      });
    });
  }

  function renderFilteredLedgerEntries() {
    let filtered = allLedgerEntries;
    if (currentSelectedCategory !== "ALL") {
      filtered = allLedgerEntries.filter(
        (e) => e.category === currentSelectedCategory,
      );
    }
    renderLedgerEntries(filtered);
  }

  function humanizeAccountName(acc) {
    const map = {
      "Assets:Cash": "Tài Khoản Tiền Mặt",
      "Assets:StockInventory": "Kho Cổ Phiếu",
      "Assets:DividendReceivable": "Cổ Tức Phải Thu",
      "Equity:Capital": "Nguồn Vốn Đầu Tư",
      "Expenses:TransactionFee": "Phí Giao Dịch TCBS",
      "Expenses:TransactionTax": "Thuế Bán Cổ Phiếu (0.1%)",
      "Expenses:DividendTax": "Thuế Cổ Tức (5%)",
      "Revenue:DividendIncome": "Doanh Thu Cổ Tức",
    };
    return map[acc] || acc;
  }

  function humanizeAccountType(type) {
    const map = {
      ASSET: "Tài Sản",
      EXPENSE: "Chi Phí",
      EQUITY: "Vốn Chủ",
      REVENUE: "Doanh Thu",
    };
    return map[type] || type;
  }

  function humanizeDescription(desc) {
    if (!desc) return "";
    if (desc === "Capital Injection") return "Nộp thêm vốn đầu tư";
    if (desc.startsWith("BUY ")) {
      return desc.replace(
        /^BUY\s+([\d.]+)\s+([A-Z0-9]+)\s+@\s+([\d.]+)/,
        (m, qty, code, price) => {
          return `Mua ${Number(qty).toLocaleString("en-US")} CP ${code} @ ${Number(price).toLocaleString("en-US")} đ`;
        },
      );
    }
    if (desc.startsWith("SELL ")) {
      return desc.replace(
        /^SELL\s+([\d.]+)\s+([A-Z0-9]+)\s+@\s+([\d.]+)/,
        (m, qty, code, price) => {
          return `Bán ${Number(qty).toLocaleString("en-US")} CP ${code} @ ${Number(price).toLocaleString("en-US")} đ`;
        },
      );
    }
    if (desc.startsWith("Settle cash dividend for ")) {
      return desc.replace(
        "Settle cash dividend for ",
        "Thanh toán cổ tức tiền mặt ",
      );
    }
    if (desc.startsWith("Accrue cash dividend for ")) {
      return desc.replace(
        "Accrue cash dividend for ",
        "Ghi nhận quyền cổ tức ",
      );
    }
    return desc;
  }

  function renderLedgerEntries(entries) {
    if (entries.length === 0) {
      containerList.innerHTML =
        '<div class="empty-msg">Chưa có bút toán kế toán nào.</div>';
      return;
    }

    let html = "";
    entries.forEach((e) => {
      html += `
        <div class="ledger-entry-card">
          <div class="entry-header">
            <span class="entry-date">${e.entry_date}</span>
            <span class="entry-desc">${humanizeDescription(e.description)}</span>
          </div>
          <div class="postings-table">
            <div class="postings-head">
              <span>Tài Khoản Kế Toán</span>
              <span style="text-align: center;">Loại</span>
              <span style="text-align: right;">Nợ</span>
              <span style="text-align: right;">Có</span>
              <span style="text-align: center;">Mã CP</span>
            </div>
            ${e.postings
              .map(
                (p) => `
              <div class="posting-row">
                <span class="account-name" title="${humanizeAccountName(p.account_name)}">${humanizeAccountName(p.account_name)}</span>
                <span class="account-type">${humanizeAccountType(p.account_type)}</span>
                <span class="debit-val">${p.debit > 0 ? p.debit.toLocaleString("en-US") + " đ" : "-"}</span>
                <span class="credit-val">${p.credit > 0 ? p.credit.toLocaleString("en-US") + " đ" : "-"}</span>
                <span class="stock-code">${p.stock_id ? '<span class="stock-badge">' + p.stock_id + "</span>" : "-"}</span>
              </div>
            `,
              )
              .join("")}
          </div>
        </div>
      `;
    });

    containerList.innerHTML = html;
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }
});
