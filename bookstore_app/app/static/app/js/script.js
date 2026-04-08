let currentBookId = null;

// Mở chi tiết sách


// Thêm vào giỏ hàng (Truyền thêm tham số e để xử lý event)
// Thêm tham số bookId vào hàm
function addToCartFromModal(e, bookId) {
    // Nếu có bookId truyền vào thì dùng, không thì mới dùng biến toàn cục
    const idToSubmit = bookId || currentBookId;

    if (!idToSubmit) {
        console.error("Không tìm thấy ID sách!");
        return;
    }

    const btn = e.currentTarget;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    // Lấy số lượng: Ở trang detail dùng name="quantity", ở Modal dùng id="buy-qty"
    const qtyInput = document.querySelector('input[name="quantity"]') || document.getElementById('buy-qty');
    const qty = qtyInput ? qtyInput.value : 1;

    const formData = new FormData();
    formData.append('quantity', qty);

    fetch(`/add-to-cart/${idToSubmit}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(res => {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Cập nhật Badge logo
            const cartBadge = document.getElementById('cart-count');
            if (cartBadge) {
                cartBadge.innerText = data.total_items;
                cartBadge.style.display = 'inline-block';
            }

            if (typeof closeModal === "function") closeModal();

            // HIỆN THÔNG BÁO TÍCH XANH + NỀN XÁM
            Swal.fire({
                title: 'Thành công!',
                text: 'Sách đã được thêm vào giỏ hàng',
                icon: 'success',
                showConfirmButton: false,
                timer: 2000,
                timerProgressBar: true,
                backdrop: `rgba(0,0,0,0.6)`, // LÀM XÁM NỀN XUNG QUANH
                showClass: { popup: 'animate__animated animate__zoomIn' },
                hideClass: { popup: 'animate__animated animate__zoomOut' }
            });
        }
    })
    .catch(err => {
        console.error("Lỗi:", err);
        Swal.fire({ icon: 'error', title: 'Lỗi', text: 'Vui lòng thử lại!' });
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
}

// Hàm bổ trợ
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function closeModal() {
    const modal = document.getElementById('bookModal');
    if(modal) modal.style.display = "none";
}

window.onclick = function(event) {
    const modal = document.getElementById('bookModal');
    if (event.target == modal) closeModal();
}