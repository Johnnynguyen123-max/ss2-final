function toggleWishlist(btn, bookId) {
    const url = '/toggle-wishlist/'; 
    
    // 1. Kiểm tra xem có đang ở trang Sách yêu thích hay không
    // (Đường dẫn của bạn là /my-wishlist/ theo cấu hình urls.py trước đó)
    const isWishlistPage = window.location.pathname.includes('my-wishlist');

    // 2. Nếu ở trang yêu thích, hiện thông báo xác nhận trước khi xóa
    if (isWishlistPage) {
        const confirmed = confirm("Bạn có muốn xóa cuốn sách này khỏi danh sách yêu thích không?");
        if (!confirmed) return; // Nếu nhấn Cancel thì dừng lại
    }

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({
            'book_id': bookId
        })
    })
    .then(response => {
        if (response.status === 403) {
            alert('Vui lòng đăng nhập để thực hiện tính năng này');
            window.location.href = '/login/'; 
            return;
        }
        return response.json();
    })
    .then(data => {
        if (data && data.status === 'success') {
            const icon = btn.querySelector('i');

            // 3. Nếu đang ở trang Sách yêu thích và vừa thực hiện 'removed'
            if (isWishlistPage && data.action === 'removed') {
                // Tìm thẻ bao ngoài cùng của sách (thẻ <a> hoặc thẻ có class book-card)
                const bookItem = btn.closest('.book-card-link') || btn.closest('.book-card');
                
                if (bookItem) {
                    // Thêm hiệu ứng mờ dần trước khi xóa
                    bookItem.style.transition = 'all 0.4s ease';
                    bookItem.style.opacity = '0';
                    bookItem.style.transform = 'scale(0.8)';
                    
                    setTimeout(() => {
                        bookItem.remove();
                        
                        // Kiểm tra nếu danh sách trống thì hiện thông báo
                        const container = document.querySelector('.book-grid');
                        if (container && container.querySelectorAll('.book-card').length === 0) {
                            container.innerHTML = '<div style="text-align: center; grid-column: 1/-1; padding: 100px 0;"><p style="color: #888;">Danh sách yêu thích của bạn đang trống.</p></div>';
                        }
                    }, 400);
                }
            } else {
                // 4. Logic đổi icon bình thường (dành cho trang chủ/chi tiết)
                if (data.is_favorite) {
                    btn.classList.add('active');
                    icon.className = 'fas fa-heart'; // Tim đặc
                } else {
                    btn.classList.remove('active');
                    icon.className = 'far fa-heart'; // Tim rỗng
                }
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
// Hàm bổ trợ lấy CSRF Token từ cookie
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