// Enhanced JavaScript with animations and better functionality

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    setupAnimations();
    loadNotifications();
}

function setupEventListeners() {
    // Like functionality
    document.addEventListener('click', handleLike);
    
    // Comment functionality
    document.addEventListener('submit', handleCommentSubmit);
    document.addEventListener('input', handleCommentInput);
    
    // Follow functionality
    document.addEventListener('click', handleFollow);
    
    // Post actions
    document.addEventListener('click', handlePostActions);
    
    // Navigation
    document.addEventListener('click', handleNavigation);
}

function setupAnimations() {
    // Add animation to all post cards
    const posts = document.querySelectorAll('.post-card');
    posts.forEach((post, index) => {
        post.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Add hover effects to buttons
    const buttons = document.querySelectorAll('.btn, .action-btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

async function handleLike(e) {
    if (e.target.closest('.like-btn') || e.target.closest('.action-btn.like')) {
        e.preventDefault();
        const likeBtn = e.target.closest('.like-btn') || e.target.closest('.action-btn.like');
        const postId = likeBtn.dataset.postId;
        
        try {
            const response = await fetch(`/like/${postId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            updateLikeUI(likeBtn, data.liked);
            updateLikeCount(likeBtn, data.liked);
            
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        }
    }
}

function updateLikeUI(likeBtn, liked) {
    const heartIcon = likeBtn.querySelector('i');
    
    if (liked) {
        likeBtn.classList.add('liked');
        heartIcon.classList.replace('far', 'fas');
        likeBtn.style.animation = 'bounce 0.6s ease';
    } else {
        likeBtn.classList.remove('liked');
        heartIcon.classList.replace('fas', 'far');
    }
    
    // Remove animation after it completes
    setTimeout(() => {
        likeBtn.style.animation = '';
    }, 600);
}

function updateLikeCount(likeBtn, liked) {
    const postCard = likeBtn.closest('.post-card');
    const likeCountElement = postCard.querySelector('.like-count');
    const currentCount = parseInt(likeCountElement.textContent) || 0;
    const newCount = liked ? currentCount + 1 : Math.max(0, currentCount - 1);
    
    likeCountElement.textContent = `${newCount} likes`;
    likeCountElement.style.animation = 'pulse 0.3s ease';
    
    setTimeout(() => {
        likeCountElement.style.animation = '';
    }, 300);
}

async function handleCommentSubmit(e) {
    if (e.target.classList.contains('comment-form')) {
        e.preventDefault();
        const form = e.target;
        const postId = form.dataset.postId;
        const commentInput = form.querySelector('.comment-input');
        const commentText = commentInput.value.trim();
        
        if (!commentText) return;
        
        // Show loading state
        const submitBtn = form.querySelector('.comment-submit');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<div class="loading"></div>';
        submitBtn.disabled = true;
        
        try {
            const response = await fetch(`/comment/${postId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ comment: commentText })
            });
            
            const data = await response.json();
            
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            if (data.success) {
                addNewComment(form, data.comment);
                commentInput.value = '';
                submitBtn.disabled = true;
                
                if (data.comment.bullying_detected) {
                    showNotification(
                        `Cyberbullying detected! Your reputation score is now ${data.comment.user_reputation}/10`, 
                        'warning'
                    );
                }
            }
            
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while posting comment', 'error');
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    }
}

function addNewComment(form, commentData) {
    const commentsContainer = form.closest('.post-card').querySelector('.post-comments');
    const newComment = document.createElement('div');
    newComment.className = `comment ${commentData.bullying_detected ? 'bullying-detected' : ''}`;
    newComment.innerHTML = `
        <img src="/static/images/${commentData.author_pic}" alt="${commentData.author}" class="comment-avatar">
        <div class="comment-content">
            <a href="/profile/${commentData.author}" class="comment-author">${commentData.author}</a>
            <div class="comment-text">${commentData.text}</div>
            <div class="comment-time">${commentData.created_at}</div>
            ${commentData.bullying_detected ? '<div class="bullying-warning">⚠️ Cyberbullying detected</div>' : ''}
        </div>
    `;
    
    commentsContainer.appendChild(newComment);
    newComment.style.animation = 'fadeIn 0.5s ease-out';
    
    // Scroll to new comment
    newComment.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function handleCommentInput(e) {
    if (e.target.classList.contains('comment-input')) {
        const submitBtn = e.target.closest('.comment-form').querySelector('.comment-submit');
        submitBtn.disabled = !e.target.value.trim();
    }
}

async function handleFollow(e) {
    if (e.target.classList.contains('follow-btn')) {
        e.preventDefault();
        const followBtn = e.target;
        const userId = followBtn.dataset.userId;
        
        // Show loading state
        const originalText = followBtn.innerHTML;
        followBtn.innerHTML = '<div class="loading"></div>';
        followBtn.disabled = true;
        
        try {
            const response = await fetch(`/follow/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            updateFollowUI(followBtn, data.following);
            
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        } finally {
            followBtn.disabled = false;
        }
    }
}

function updateFollowUI(followBtn, following) {
    if (following) {
        followBtn.textContent = 'Following';
        followBtn.classList.add('following');
        followBtn.style.background = 'var(--success)';
    } else {
        followBtn.textContent = 'Follow';
        followBtn.classList.remove('following');
        followBtn.style.background = 'var(--primary)';
    }
    
    followBtn.style.animation = 'pulse 0.3s ease';
    setTimeout(() => {
        followBtn.style.animation = '';
    }, 300);
}

function handlePostActions(e) {
    // Handle post options menu
    if (e.target.closest('.post-options')) {
        const optionsBtn = e.target.closest('.post-options');
        // Implement post options menu
        showPostOptions(optionsBtn);
    }
    
    // Handle share functionality
    if (e.target.closest('.share-btn')) {
        const shareBtn = e.target.closest('.share-btn');
        sharePost(shareBtn);
    }
}

function handleNavigation(e) {
    // Add smooth transitions to navigation links
    if (e.target.matches('a[href^="/"]') && !e.target.matches('a[target="_blank"]')) {
        e.preventDefault();
        const href = e.target.getAttribute('href');
        
        // Add page transition
        document.body.style.opacity = '0.7';
        document.body.style.transition = 'opacity 0.3s ease';
        
        setTimeout(() => {
            window.location.href = href;
        }, 300);
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `flash ${type}`;
    notification.textContent = message;
    
    const container = document.querySelector('.flash-messages') || createFlashContainer();
    container.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => notification.remove(), 500);
    }, 5000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';
    document.body.appendChild(container);
    return container;
}

function loadNotifications() {
    // Simulate loading notifications
    setTimeout(() => {
        const notificationBadges = document.querySelectorAll('.nav-link .badge');
        notificationBadges.forEach(badge => {
            badge.textContent = Math.floor(Math.random() * 5) + 1;
            badge.style.animation = 'pulse 2s infinite';
        });
    }, 2000);
}

// Share post functionality
function sharePost(shareBtn) {
    const postCard = shareBtn.closest('.post-card');
    const postId = postCard.dataset.postId;
    
    if (navigator.share) {
        navigator.share({
            title: 'Check out this post on InstaClone',
            text: 'I found this interesting post on InstaClone',
            url: `${window.location.origin}/post/${postId}`
        });
    } else {
        // Fallback: copy to clipboard
        const postUrl = `${window.location.origin}/post/${postId}`;
        navigator.clipboard.writeText(postUrl).then(() => {
            showNotification('Post link copied to clipboard!', 'success');
        });
    }
}

// Auto-hide flash messages
setTimeout(() => {
    const flashMessages = document.querySelector('.flash-messages');
    if (flashMessages) {
        flashMessages.style.transition = 'opacity 0.5s';
        flashMessages.style.opacity = '0';
        setTimeout(() => flashMessages.remove(), 500);
    }
}, 5000);

// Add CSS for fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(100%); }
    }
    
    .flash {
        transition: all 0.3s ease;
    }
`;
document.head.appendChild(style);