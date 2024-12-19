const SITES = ['tssindia', 'tsschina', 'tssavs', 'tsseurope', 'tssjapan'];

$(document).ready(function() {
    // Generate site cards dynamically
    SITES.forEach(site => {
        createSiteCard(site);
        fetchQuickStats(site);
    });

    // Attach event listeners dynamically
    $(document).on('submit', '.order-form', function(event) {
        event.preventDefault();
        const site_uid = $(this).data('site');
        const start_date = $(this).find('.start-date').val();
        const end_date = $(this).find('.end-date').val();
        fetchOrderDetails(site_uid, start_date, end_date);
    });

    $(document).on('click', '.export-button', function() {
        const site_uid = $(this).data('site');
        const start_date = $(this).siblings('.start-date').val();
        const end_date = $(this).siblings('.end-date').val();
        const orderTable = $(this).closest('.site-card').find('.order-table tbody');
        exportOrders(site_uid, start_date, end_date, orderTable);
    });
});

function createSiteCard(site) {
    const cardHtml = `
        <div class="row mb-4">
            <div class="col-md-4 order-stats-container">
                <div class="card site-card" id="${site}-quick-stats-card">
                    <div class="card-header text-uppercase">${site.toUpperCase()} Quick Stats</div>
                    <div class="card-body">
                        <div class="dashboard-section quick-stats-section">
                            <div class="quick-stats">
                                <div class="stat-box today-orders">Today's Orders: <span>-</span></div>
                                <div class="stat-box yesterday-orders">Yesterday's Orders: <span>-</span></div>
                                <div class="stat-box month-orders">This Month's Orders: <span>-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-8 order-details-container">
                <div class="card site-card" id="${site}-order-details-card">
                    <div class="card-header text-uppercase">${site.toUpperCase()} Order Details</div>
                    <div class="card-body">
                        <div class="dashboard-section order-details-section">
                            <form class="order-form date-form" data-site="${site}">
                                <div class="row">
                                    <div class="col">
                                        <label>From Date</label>
                                        <input type="date" class="form-control start-date" required>
                                    </div>
                                    <div class="col">
                                        <label>To Date</label>
                                        <input type="date" class="form-control end-date" required>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-primary mt-2">Fetch Orders</button>
                                <button type="button" class="btn btn-success mt-2 export-button" data-site="${site}" style="display:none;">Export Orders</button>
                            </form>
                            <div class="order-summary">
                                <table class="table table-bordered order-table">
                                    <thead>
                                        <tr>
                                            <th>Date</th>
                                            <th>Status</th>
                                            <th>Order Number</th>
                                            <th>Purchase Order Number</th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    $('#siteCardsContainer').append(cardHtml);
}

function fetchQuickStats(site_uid) {
    $.ajax({
        url: '/fetch_order_counts',
        method: 'GET',
        data: { site: site_uid },
        success: function(response) {
            $(`#${site_uid}-quick-stats-card .today-orders span`).text(response.todaysOrders);
            $(`#${site_uid}-quick-stats-card .yesterday-orders span`).text(response.yesterdaysOrders);
            $(`#${site_uid}-quick-stats-card .month-orders span`).text(response.thisMonthOrders);
        },
        error: function() {
            $(`#${site_uid}-quick-stats-card .today-orders span`).text('Error');
            $(`#${site_uid}-quick-stats-card .yesterday-orders span`).text('Error');
            $(`#${site_uid}-quick-stats-card .month-orders span`).text('Error');
        }
    });
}

function fetchOrderDetails(site_uid, start_date, end_date) {
    $.ajax({
        url: '/fetch_orders',
        method: 'POST',
        data: { site_uid, start_date, end_date },
        success: function(response) {
            const orderTableBody = $(`#${site_uid}-order-details-card .order-table tbody`);
            orderTableBody.empty();

            if (response.length > 0) {
                response.forEach(order => {
                    orderTableBody.append(`
                        <tr>
                            <td>${order.date}</td>
                            <td>${order.order_status}</td>
                            <td>${order.order_no}</td>
                            <td>${order.purchaseOrderNumber}</td>
                        </tr>
                    `);
                });
                $(`#${site_uid}-order-details-card .export-button`).show();
            } else {
                orderTableBody.append('<tr><td colspan="4">No orders found for the selected date range.</td></tr>');
                $(`#${site_uid}-order-details-card .export-button`).hide();
            }
        }
    });
}

function exportOrders(site_uid, start_date, end_date, orderTable) {
    const orders = [];
    orderTable.find('tr').each(function() {
        const order = {
            date: $(this).find('td').eq(0).text(),
            order_status: $(this).find('td').eq(1).text(),
            order_no: $(this).find('td').eq(2).text(),
            purchaseOrderNumber: $(this).find('td').eq(3).text()
        };
        orders.push(order);
    });
    $.ajax({
        url: '/export_orders',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ orders, site_uid, from_date: start_date, to_date: end_date }),
        success: function(response) {
            const blob = new Blob([response], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${site_uid}-${start_date}-to-${end_date}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        }
    });
}