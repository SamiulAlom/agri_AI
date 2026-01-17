const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatWindow = document.getElementById('chat-window');
const messagesDiv = document.getElementById('messages');
const loadingIndicator = document.getElementById('loading');

// Function to scroll chat to the bottom
function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Function to append a message bubble
function appendMessage(role, text) {
    const wrapper = document.createElement('div');
    wrapper.className = role === 'user' ? 'flex justify-end' : 'flex justify-start';

    const bubble = document.createElement('div');
    bubble.className = role === 'user' ? 'user-bubble p-4 max-w-[80%] shadow-sm' : 'bot-bubble p-4 max-w-[80%] shadow-sm';
    bubble.innerText = text;

    wrapper.appendChild(bubble);
    messagesDiv.appendChild(wrapper);
    scrollToBottom();
}

// Handle Form Submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;

    // 1. Add User Message to UI
    appendMessage('user', message);
    userInput.value = '';

    // 2. Show Loading Spinner
    loadingIndicator.classList.remove('hidden');
    scrollToBottom();

    try {
        // 3. Send to Flask Backend
        const response = await fetch('/get_response', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        // 4. Hide Loading and Add Bot Response
        loadingIndicator.classList.add('hidden');
        if (data.response) {
            appendMessage('bot', data.response);
        } else {
            appendMessage('bot', 'দুঃখিত, বর্তমানে কিছু সমস্যা হচ্ছে। আবার চেষ্টা করুন।');
        }
    } catch (error) {
        loadingIndicator.classList.add('hidden');
        appendMessage('bot', 'সার্ভারে সংযোগ দেওয়া যাচ্ছে না।');
    }
});

// Function to clear chat memory
async function clearChat() {
    if (confirm('আপনি কি নিশ্চিত যে আপনি চ্যাট ইতিহাস মুছে ফেলতে চান?')) {
        await fetch('/clear_chat', { method: 'POST' });
        messagesDiv.innerHTML = '';
        appendMessage('bot', 'চ্যাট ইতিহাস মুছে ফেলা হয়েছে। আমি আপনাকে কিভাবে সাহায্য করতে পারি?');
    }
}