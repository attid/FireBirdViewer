/* FireBird Viewer - client-side utilities */

/* Auto-dismiss toast notifications after 4 seconds */
document.addEventListener('htmx:afterSwap', function() {
    const container = document.getElementById('toast-container');
    if (container && container.children.length > 0) {
        const alerts = container.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            setTimeout(function() {
                alert.parentElement?.remove();
            }, 4000);
        });
    }
});
