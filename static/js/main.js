// 메인 JavaScript

console.log('YG-Manager 시스템이 로드되었습니다.');

// API 호출 헬퍼
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {'Content-Type': 'application/json'}
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(endpoint, options);
    return await response.json();
}

// 메시지 표시
function showMessage(message, type = 'info') {
    const alertClass = `alert alert-${type}`;
    const alertHTML = `<div class="${alertClass}">${message}</div>`;
    // TODO: 메시지 표시 UI 구현
    console.log(`[${type.toUpperCase()}] ${message}`);
}
