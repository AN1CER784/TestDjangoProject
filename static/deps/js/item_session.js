document.getElementById("buy-btn").addEventListener("click", () => {
    fetch(item_url)
        .then(res => res.json())
        .then(data => {
            return stripe.redirectToCheckout({sessionId: data.sessionId});
        })
        .then(result => {
            if (result.error) {
                alert(result.error.message);
            }
        });
});