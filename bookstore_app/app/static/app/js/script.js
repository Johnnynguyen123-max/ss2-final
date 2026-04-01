// Biến toàn cục để lưu ID sách đang hiển thị trong Modal
let currentBookId = null;

function openBookDetail(bookId) {
    currentBookId = bookId;
    const modal = document.getElementById('bookModal');
    
    // Hiện modal ngay lập tức với trạng thái đang tải
    modal.style.display = "block";
    document.getElementById('imageLoader').style.display = "flex";
    document.getElementById('modalImage').style.display = "none";

    fetch(`/book-detail/${bookId}/`)
    .then(response => response.json())
    .then(data => {
        // Đổ dữ liệu vào các ID đã có trong HTML của bạn
        document.getElementById('modalTitle').innerText = data.title;
        document.getElementById('modalAuthor').innerText = data.author;
        document.getElementById('modalPrice').innerText = data.price + "đ";
        document.getElementById('modalDescription').innerText = data.description;
        
        // Hiển thị ảnh
        const modalImg = document.getElementById('modalImage');
        modalImg.src = data.image_url;
        modalImg.onload = function() {
            document.getElementById('imageLoader').style.display = "none";
            modalImg.style.display = "block";
        };
    })
    .catch(err => console.error("Lỗi fetch dữ liệu:", err));
}

// ĐỔI TÊN HÀM để khớp với HTML (onclick="addToCartFromModal()")
function addToCartFromModal() {
    if (!currentBookId) return;

    const qtyInput = document.getElementById('buy-qty');
    const qty = qtyInput ? qtyInput.value : 1;

    // Hiệu ứng nút
    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang thêm...';

    // Dùng FormData để Django nhận được request.POST
    const formData = new FormData();
    formData.append('quantity', qty);

    fetch(`/add-to-cart/${currentBookId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest' // Để Django biết đây là Ajax
        },
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        // Cập nhật con số trên Badge (Sử dụng ID để chính xác hơn)
        const cartBadge = document.getElementById('cart-count'); // Đã sửa id ở bước trước
        if (cartBadge) {
            cartBadge.innerText = data.total_items;
            cartBadge.style.transform = 'scale(1.4)';
            setTimeout(() => cartBadge.style.transform = 'scale(1)', 200);
        }
        
        btn.disabled = false;
        btn.innerHTML = originalText;
        alert("Đã thêm vào giỏ hàng thành công!");
    })
    .catch(err => {
        console.error("Lỗi giỏ hàng:", err);
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
}

// Hàm lấy CSRF Token
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
    document.getElementById('bookModal').style.display = "none";
}

// Đóng modal khi click ra ngoài
window.onclick = function(event) {
    const modal = document.getElementById('bookModal');
    if (event.target == modal) {
        closeModal();
    }
}