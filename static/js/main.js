// static/js/main.js
let currentLanguage = 'en';
let chatSessionId = null;
let lastAnalysisResults = null;
let currentMode = 'contract';
let searchTimeout = null;

function updateLanguageStrings() {
    const elements = document.querySelectorAll('[data-lang-key]');
    elements.forEach(element => {
        const key = element.getAttribute('data-lang-key');
        if (translations[currentLanguage]?.[key]) {
            if (element.tagName === 'TEXTAREA' || (element.tagName === 'INPUT' && element.type === 'text')) {
                element.placeholder = translations[currentLanguage][key];
            } else if (element.tagName === 'LABEL' && element.classList.contains('chip')) {
                element.textContent = translations[currentLanguage][key];
                element.setAttribute('title', translations[currentLanguage][key + '_desc'] || translations[currentLanguage][key]);
            } else {
                element.textContent = translations[currentLanguage][key];
            }
        }
    });
}

function updateMarksTranslations() {
    const markElements = document.querySelectorAll('[data-mark-key]');
    markElements.forEach(element => {
        const key = element.getAttribute('data-mark-key');
        const translatedText = translations[currentLanguage]?.marks?.[key] || formatTitle(key);
        element.textContent = translatedText;
    });
}

function changeLanguage() {
    const newLanguage = document.getElementById('languageSelect').value;
    if (currentLanguage === newLanguage) return;

    console.log(`Changing language from ${currentLanguage} to ${newLanguage}`);
    currentLanguage = newLanguage;
    localStorage.setItem('preferredLanguage', currentLanguage);

    updateLanguageStrings();
    updateMarksTranslations();

    if (lastAnalysisResults) {
        console.log('Retranslating analysis results');
        retranslateAnalysisResults(currentLanguage);
    } else {
        console.log('No analysis results to retranslate, updating chat language');
        updateChatLanguage(currentLanguage);
    }
}

function disableInputsDuringRetranslation(disable) {
    const languageSelect = document.getElementById('languageSelect');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');
    
    languageSelect.disabled = disable;
    chatInput.disabled = disable;
    sendButton.disabled = disable;
}

async function retranslateAnalysisResults(language) {
    try {
        document.getElementById('analysisStatus').style.display = 'block';
        updateProgress(1, 2, translations[currentLanguage]?.translating || 'Translating analysis...', true);
        disableInputsDuringRetranslation(true);

        console.log(`Sending /retranslate request for ${language}`);
        const response = await fetch('/retranslate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ language })
        });

        const data = await response.json();
        console.log(`Retranslate response for ${language}:`, data);

        if (!response.ok) {
            console.error(`Retranslation failed with status ${response.status}: ${data.error}`);
            throw new Error(data.error || `Retranslation failed: ${response.status}`);
        }

        if (data.status === 'success') {
            lastAnalysisResults = data;
            displayAnalysisResults(data);
            updateProgress(2, 2, translations[currentLanguage]?.translation_complete || 'Translation complete');
            console.log(`Successfully retranslated to ${language}`);
            await restartChat(language);
        } else {
            console.error(`Translation error for ${language}: ${data.error}`);
            throw new Error(data.error || 'Retranslation failed');
        }
    } catch (error) {
        console.error(`Retranslation error for ${language}:`, error);
        showError(`${translations[currentLanguage]?.retranslation_error || 'Translation error'}: ${error.message}`);
        if (lastAnalysisResults) {
            console.log('Falling back to last analysis results:', lastAnalysisResults);
            displayAnalysisResults(lastAnalysisResults);
        } else {
            document.getElementById('results').style.display = 'none';
        }
    } finally {
        document.getElementById('analysisStatus').style.display = 'none';
        disableInputsDuringRetranslation(false);
    }
}

async function restartChat(language) {
    console.log(`Restarting chat in language: ${language}`);
    await endChatSession();
    if (lastAnalysisResults && lastAnalysisResults.document_text) {
        await initializeChat(lastAnalysisResults.document_text);
        await updateChatLanguage(language);
    } else {
        console.warn('No contract text available to restart chat');
    }
}

async function updateChatLanguage(language) {
    try {
        const response = await fetch('/api/chat/update_language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ language })
        });

        if (!response.ok) {
            throw new Error(`Chat language update failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.error || 'Chat language update failed');
        }
        console.log(`Chat language updated to ${language}`);
    } catch (error) {
        console.error('Chat language update error:', error);
        showError(`${translations[currentLanguage]?.chat_language_error || 'Chat language error'}: ${error.message}`);
    }
}

async function initializeChat(contractText) {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) chatMessages.innerHTML = '';

    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');
    chatInput.disabled = true;
    sendButton.disabled = true;

    if (!contractText) {
        console.warn('No contract text for chat initialization');
        return;
    }

    try {
        console.log('Starting chat session');
        const response = await fetch('/api/chat/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contract_text: contractText,
                language: currentLanguage
            })
        });

        if (!response.ok) {
            throw new Error(`Chat start failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
            chatSessionId = data.session_id;
            console.log('Chat session started:', chatSessionId);
            chatInput.disabled = false;
            sendButton.disabled = false;
        } else {
            throw new Error(data.error || 'Chat initialization failed');
        }
    } catch (error) {
        console.error('Chat initialization error:', error);
        showError(`${translations[currentLanguage]?.chat_init_error || 'Chat initialization failed'}: ${error.message}`);
        chatInput.disabled = true;
        sendButton.disabled = true;
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();

    if (!message) return;

    if (!chatSessionId) {
        showError(translations[currentLanguage]?.no_chat_session || 'No active chat session. Please analyze a contract.');
        return;
    }

    displayChatMessage(message, true);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    document.getElementById('sendMessage').disabled = true;
    chatInput.disabled = true;

    displayTypingIndicator();

    try {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                language: currentLanguage
            })
        });

        if (!response.ok) {
            throw new Error(`Chat message failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
            removeTypingIndicator();
            displayChatMessage(data.response);
        } else {
            throw new Error(data.error || 'Failed to process message');
        }
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator();
        displayChatMessage(`${translations[currentLanguage]?.chat_error || 'Error'}: ${error.message}`);
    } finally {
        chatInput.disabled = false;
        document.getElementById('sendMessage').disabled = false;
    }
}

async function endChatSession() {
    if (!chatSessionId) return;

    try {
        const response = await fetch('/api/chat/end', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        if (data.status === 'success') {
            console.log('Chat session ended');
        } else {
            console.warn('Failed to end chat session:', data.error);
        }
    } catch (error) {
        console.error('Error ending chat session:', error);
    } finally {
        chatSessionId = null;
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendMessage');
        if (chatInput) chatInput.disabled = true;
        if (sendButton) sendButton.disabled = true;
    }
}

async function handleFileUpload(event) {
    event.preventDefault();
    console.log('Handling file upload');

    const resultsContainer = document.getElementById('results');
    resultsContainer.style.display = 'none';

    const fileInput = document.getElementById('contractFile');
    const languageSelect = document.getElementById('languageSelect');

    if (!fileInput.files || fileInput.files.length === 0) {
        showError(translations[currentLanguage]?.no_file_selected || 'Please select a file.');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('language', languageSelect.value);

    document.getElementById('analysisStatus').style.display = 'block';
    updateProgress(1, 4, translations[currentLanguage]?.extracting_text || 'Extracting text...', true);

    try {
        console.log('Sending /api/document/extract request');
        const extractResponse = await fetch('/api/document/extract', {
            method: 'POST',
            body: formData
        });

        if (!extractResponse.ok) {
            const errorData = await extractResponse.json();
            throw new Error(errorData.error || 'Text extraction failed');
        }

        const extractData = await extractResponse.json();
        if (extractData.status !== 'success') {
            throw new Error(extractData.error || 'Text extraction failed');
        }

        updateProgress(2, 4, translations[currentLanguage]?.analyzing_contract || 'Analyzing contract...', true);

        console.log('Sending /analyze request');
        const analyzeResponse = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: extractData.text,
                language: languageSelect.value
            })
        });

        if (!analyzeResponse.ok) {
            const errorData = await analyzeResponse.json();
            throw new Error(errorData.error || 'Analysis failed');
        }

        const analysisData = await analyzeResponse.json();
        console.log('Analysis response:', analysisData);

        if (analysisData.status === 'success') {
            lastAnalysisResults = analysisData;
            updateProgress(4, 4, translations[currentLanguage]?.analysis_complete || 'Analysis complete');
            console.log('Calling displayAnalysisResults with data:', analysisData);
            displayAnalysisResults(analysisData);
            await initializeChat(analysisData.document_text);
            console.log('Forcing results visibility');
            resultsContainer.style.display = 'block';
        } else {
            throw new Error(analysisData.error || 'Analysis failed');
        }
    } catch (error) {
        console.error('File upload error:', error);
        showError(`${translations[currentLanguage]?.error_occurred || 'Error'}: ${error.message}`);
    } finally {
        document.getElementById('analysisStatus').style.display = 'none';
    }
}

function updateProgress(step, total, message, showBlink = false) {
    const progressFill = document.querySelector('.progress-fill');
    const statusMessage = document.getElementById('statusMessage');
    const blinkingText = document.getElementById('blinkingText');
    progressFill.style.width = `${(step / total) * 100}%`;
    statusMessage.textContent = message;
    if (showBlink) {
        if (!blinkingText) {
            const blinkDiv = document.createElement('div');
            blinkDiv.id = 'blinkingText';
            blinkDiv.className = 'blinking-text';
            blinkDiv.textContent = translations[currentLanguage]?.performing_analysis || 'Processing...';
            statusMessage.insertAdjacentElement('afterend', blinkDiv);
        } else {
            blinkingText.textContent = translations[currentLanguage]?.performing_analysis || 'Processing...';
        }
    } else if (blinkingText) {
        blinkingText.remove();
    }
}

function showError(message, isSuccess = false) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.className = `error-message ${isSuccess ? 'success-message' : ''}`;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function displayAnalysisResults(data) {
    console.log('Received analysis data:', JSON.stringify(data, null, 2));

    if (!data || data.status !== 'success') {
        console.error('Invalid analysis data:', data);
        showError(translations[currentLanguage]?.error_occurred || 'Failed to display results.');
        document.getElementById('results').style.display = 'none';
        return;
    }

    lastAnalysisResults = data;

    localStorage.setItem('analysisData', JSON.stringify({
        contract_text: data.document_text,
        shadow_analysis: data.shadow_analysis,
        summary_analysis: data.summary
    }));

    console.log('Clearing DOM elements');
    document.getElementById('summaryContent').innerHTML = '';
    document.getElementById('scoresGrid').innerHTML = '';
    document.getElementById('shadowContent').innerHTML = '';

    console.log('Rendering contract text');
    document.getElementById('summaryContent').innerHTML = `
        <div class="summary-section">
            <h3 data-lang-key="contract_text">${translations[currentLanguage]?.contract_text || 'Contract Text'}</h3>
            <pre class="contract-text">${(data.document_text || '').replace(/\n/g, '<br>')}</pre>
        </div>
    `;

    console.log('Displaying contract summary:', data.summary);
    displayContractSummary(data.summary || {});
    console.log('Displaying scores grid:', data.summary?.structured_analysis);
    displayScoresGrid(data.summary?.structured_analysis || {});
    console.log('Displaying shadow analysis:', data.shadow_analysis);
    displayShadowAnalysis({ content: data.shadow_analysis || '' });
    console.log('Updating score badges:', data.evaluation);
    updateScoreBadges(data.evaluation || {});
    updateLanguageStrings();
    updateMarksTranslations();

    console.log('Setting results display to block');
    document.getElementById('results').style.display = 'block';
    console.log('Results displayed successfully');
}

function displayContractSummary(summary) {
    console.log('Displaying summary:', summary);

    const keyPoints = typeof summary?.key_points === 'string' && summary.key_points.trim()
        ? summary.key_points.split('\n').filter(p => p.trim())
        : [];
    const potentialIssues = typeof summary?.potential_issues === 'string' && summary.potential_issues.trim()
        ? summary.potential_issues.split('\n').filter(p => p.trim())
        : [];
    const recommendations = typeof summary?.recommendations === 'string' && summary.recommendations.trim()
        ? summary.recommendations.split('\n').filter(p => p.trim())
        : [];

    const summaryContent = document.getElementById('summaryContent');
    summaryContent.innerHTML += `
        <div class="summary-section">
            <h3 data-lang-key="executive_summary">${translations[currentLanguage]?.executive_summary || 'Executive Summary'}</h3>
            <p>${summary?.executive_summary || translations[currentLanguage]?.no_summary || 'No summary available'}</p>
            <div class="summary-details">
                <h4 data-lang-key="key_points">${translations[currentLanguage]?.key_points || 'Key Points'}</h4>
                <ul class="data-list">
                    ${keyPoints.length > 0 ? keyPoints.map(point => `<li>${point}</li>`).join('') : `<li>${translations[currentLanguage]?.no_key_points || 'No key points available'}</li>`}
                </ul>
                <h4 data-lang-key="potential_issues">${translations[currentLanguage]?.potential_issues || 'Potential Issues'}</h4>
                <ul class="data-list">
                    ${potentialIssues.length > 0 ? potentialIssues.map(issue => `<li>${issue}</li>`).join('') : `<li>${translations[currentLanguage]?.no_issues || 'No issues identified'}</li>`}
                </ul>
                <h4 data-lang-key="recommendations">${translations[currentLanguage]?.recommendations || 'Recommendations'}</h4>
                <ul class="data-list">
                    ${recommendations.length > 0 ? recommendations.map(rec => `<li>${rec}</li>`).join('') : `<li>${translations[currentLanguage]?.no_recommendations || 'No recommendations provided'}</li>`}
                </ul>
            </div>
        </div>
    `;
}

function displayScoresGrid(analysis) {
    console.log('Rendering scores grid with analysis:', analysis);

    const scoresHtml = Object.entries(analysis || {})
        .filter(([key]) => key !== 'overall_score')
        .map(([key, value]) => {
            const translatedTitle = translations[currentLanguage]?.marks?.[key] || formatTitle(key);
            return `
                <div class="score-card ${getScoreClass(value?.score)}">
                    <div class="score-header">
                        <h4 data-mark-key="${key}">${translatedTitle}</h4>
                        <div class="score-info">
                            <span class="score-badge">${value?.score || 0}/10</span>
                        </div>
                    </div>
                    ${value?.content ? `<div class="score-content"><p>${value.content}</p></div>` : ''}
                </div>
            `;
        })
        .join('');

    document.getElementById('scoresGrid').innerHTML = scoresHtml;
}

function displayShadowAnalysis(shadowData) {
    const shadowContent = document.getElementById('shadowContent');
    shadowContent.innerHTML = `
        <div class="shadow-section">
            <div class="shadow-text">
                ${formatShadowContent(shadowData.content || '')}
            </div>
        </div>
    `;
}

function formatShadowContent(content) {
    if (!content) return '<p>No analysis available</p>';
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/^### (.*)$/gm, '<h3>$1</h3>')
        .replace(/^#### (.*)$/gm, '<h4>$1</h4>')
        .replace(/^\* (.*)$/gm, '<li>$1</li>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/<p>\s*<li>/g, '<ul><li>')
        .replace(/<\/li>\s*<li>/g, '</li><li>')
        .replace(/<\/li>\s*<\/p>/g, '</li></ul></p>')
        .trim();
}

function updateScoreBadges(evaluation) {
    const overallScore = (evaluation?.evaluation?.overall_score || 0) * 10;
    document.getElementById('summaryScore').innerHTML = `
        <div class="score-value">${Math.round(overallScore)}%</div>
        <div class="score-label" data-lang-key="overall_score">Overall Score</div>
    `;
    document.getElementById('shadowScore').innerHTML = `
        <div class="score-value">${Math.round(overallScore)}%</div>
        <div class="score-label" data-lang-key="analysis_accuracy">Analysis Accuracy</div>
    `;
}

function getScoreClass(score) {
    if (!score || score <= 3) return "low-score";
    if (score >= 8) return "high-score";
    return "";
}

function formatTitle(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function displayChatMessage(message, isUser = false) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${isUser ? 'user-message' : 'bot-message'}`;
    
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    const formattedMessage = message
        .split('\n\n')
        .map(para => {
            if (para.includes('\n- ')) {
                const items = para.split('\n- ').filter(item => item.trim());
                const listItems = items.map((item, index) => {
                    const text = index === 0 ? item : item.replace(/^- /, '');
                    return text.trim() ? `<li>${text.trim()}</li>` : '';
                }).join('');
                return `<ul>${listItems}</ul>`;
            }
            return `<p>${para.trim()}</p>`;
        })
        .join('');

    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}">
                ${isUser ? '🙂' : '🤖'}
            </div>
            <div class="message-text">
                ${formattedMessage}
                <span class="message-timestamp">${timestamp}</span>
            </div>
        </div>
    `;
    
    messageDiv.style.opacity = '0';
    chatMessages.appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateY(0)';
    }, 10);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function displayTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'chat-message bot-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar bot-avatar">🤖</div>
            <div class="message-text">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function switchMode(mode) {
    const contractSection = document.getElementById('contractSection');
    const studentSection = document.getElementById('studentSection');
    const contractBtn = document.getElementById('contractModeBtn');
    const studentBtn = document.getElementById('studentModeBtn');

    localStorage.setItem('currentMode', mode);
    currentMode = mode;

    if (mode === 'contract') {
        contractSection.style.display = 'block';
        studentSection.style.display = 'none';
        contractBtn.classList.add('active');
        studentBtn.classList.remove('active');
    } else {
        contractSection.style.display = 'none';
        studentSection.style.display = 'block';
        contractBtn.classList.remove('active');
        studentBtn.classList.add('active');
    }
}

async function fetchUniversitySuggestions(query) {
    try {
        const response = await fetch(`http://universities.hipolabs.com/search?name=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Failed to fetch universities');
        const data = await response.json();
        return data.slice(0, 5).map(uni => uni.name);
    } catch (error) {
        console.error('University suggestion error:', error);
        return [];
    }
}

async function fetchKeywordSuggestions(category) {
    // Mock suggestions; replace with backend endpoint if available
    const suggestions = {
        working_student: ['part-time work', 'student jobs', 'work regulations'],
        housing: ['dormitory', 'student accommodation', 'rent costs'],
        research: ['research programs', 'thesis opportunities', 'labs'],
        internship: ['internship programs', 'placements', 'traineeships'],
        job_offers: ['career fairs', 'job postings', 'employment'],
        scholarships: ['financial aid', 'grants', 'bursaries'],
        visas: ['student visa', 'residence permit', 'immigration'],
        custom: ['enter keywords', 'specific terms', 'custom query']
    };
    return suggestions[category] || [];
}

function displaySuggestions(suggestions, containerId, selectCallback) {
    const container = document.getElementById(containerId);
    container.innerHTML = suggestions.length ? suggestions.map(item => `
        <div class="suggestion-item" role="button" tabindex="0">${item}</div>
    `).join('') : '<div class="suggestion-item no-suggestions">No suggestions</div>';

    container.querySelectorAll('.suggestion-item:not(.no-suggestions)').forEach(item => {
        item.addEventListener('click', () => {
            selectCallback(item.textContent);
            container.innerHTML = '';
        });
        item.addEventListener('keypress', e => {
            if (e.key === 'Enter') {
                selectCallback(item.textContent);
                container.innerHTML = '';
            }
        });
    });
}

// Modified: Enhanced student search with event delegation and form reset
let isSearching = false;
async function handleStudentSearch(event) {
    event.preventDefault();
    console.log('Student search form submitted at', new Date().toISOString()); // Debug: Confirm submission

    if (isSearching) {
        console.log('Search in progress, ignoring new submission');
        return;
    }
    isSearching = true;

    const studentForm = document.getElementById('studentSearchForm');
    const universityInput = document.getElementById('universityInput');
    const category = document.querySelector('input[name="category"]:checked')?.value;
    const customKeywords = document.getElementById('customKeywords')?.value.trim();
    const searchButton = document.querySelector('#studentSearchForm button[type="submit"]');

    if (!studentForm) {
        console.error('Student search form not found in DOM');
        isSearching = false;
        return;
    }

    if (!universityInput.value.trim()) {
        showError(translations[currentLanguage]?.no_university || 'Please enter a university name.');
        universityInput.focus();
        isSearching = false;
        return;
    }

    if (category === 'custom' && !customKeywords) {
        showError(translations[currentLanguage]?.no_keywords || 'Please enter custom keywords.');
        document.getElementById('customKeywords').focus();
        isSearching = false;
        return;
    }

    if (searchButton) searchButton.disabled = true;

    try {
        console.log(`Sending student search: university=${universityInput.value}, category=${category}, keywords=${customKeywords || 'none'}`);
        const loadingSpinner = document.getElementById('loadingSpinner');
        loadingSpinner.style.display = 'flex';
        document.getElementById('searchResults').innerHTML = '';

        const response = await fetch('/api/student/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                university: universityInput.value,
                category,
                keywords: category === 'custom' ? customKeywords.split(',').map(k => k.trim()).filter(k => k) : undefined,
                language: currentLanguage
            })
        });

        console.log('Search API response status:', response.status);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Search failed');
        }

        const data = await response.json();
        console.log('Student search response:', data);
        displayStudentResults(data);
    } catch (error) {
        console.error('Student search error:', error);
        showError(`${translations[currentLanguage]?.error_occurred || 'Search failed'}: ${error.message}`);
        document.getElementById('searchResults').innerHTML = `<p class="error-message">${error.message}</p>`;
    } finally {
        loadingSpinner.style.display = 'none';
        if (searchButton) searchButton.disabled = false;
        isSearching = false;
        // Reset form to ensure clean state
        studentForm.reset();
        document.getElementById('customKeywordsContainer').style.display = category === 'custom' ? 'block' : 'none';
        console.log('Form reset and search state cleared');
    }
}

function displayStudentResults(data) {
    const resultsDiv = document.getElementById('searchResults');
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '';

    if (data.status === 'error') {
        resultsDiv.innerHTML = `<p class="error-message">${translations[currentLanguage]?.error_occurred || 'Error'}: ${data.error}</p>`;
        return;
    }

    const { university, category, summary, results, total_results } = data;
    const categoryName = category === 'custom' 
        ? (translations[currentLanguage]?.category_custom || 'Custom Search')
        : (translations[currentLanguage]?.[`category_${category}`] || formatTitle(category));
    
    resultsDiv.innerHTML = `
        <div class="search-summary">
            <h3 data-lang-key="search_results">${translations[currentLanguage]?.search_results || 'Search Results'}</h3>
            <p data-lang-key="results_for">${translations[currentLanguage]?.results_for || 'Results for'} ${categoryName} at ${university}</p>
            <p data-lang-key="found_results">${translations[currentLanguage]?.found_results || 'Found'} ${total_results} ${translations[currentLanguage]?.relevant_results || 'relevant results'}</p>
            <p><strong>${translations[currentLanguage]?.summary || 'Summary'}:</strong> ${summary.recommendation || 'No summary provided'}</p>
            <div class="sort-controls">
                <label for="sortResults">${translations[currentLanguage]?.sort_by || 'Sort by'}:</label>
                <select id="sortResults" aria-label="Sort search results">
                    <option value="relevance">${translations[currentLanguage]?.sort_relevance || 'Relevance'}</option>
                    <option value="title">${translations[currentLanguage]?.sort_title || 'Title'}</option>
                </select>
            </div>
        </div>
    `;

    if (total_results === 0) {
        const guessedDomain = university.toLowerCase().replace(/[\s\W]+/g, '-') + '.edu';
        resultsDiv.innerHTML += `
            <p>${translations[currentLanguage]?.no_results || 'No regulations found for'} ${categoryName}. 
            ${translations[currentLanguage]?.try_another || 'Try another category or visit'} 
            <a href="https://${guessedDomain}" target="_blank">${university} ${translations[currentLanguage]?.website || 'website'}</a>.</p>
        `;
        return;
    }

    const sortedResults = [...results];
    const sortSelect = resultsDiv.querySelector('#sortResults');
    sortSelect.addEventListener('change', () => {
        console.log('Sorting results by:', sortSelect.value);
        const sortBy = sortSelect.value;
        sortedResults.sort((a, b) => {
            if (sortBy === 'relevance') return b.relevance_score - a.relevance_score;
            if (sortBy === 'title') return a.title.localeCompare(b.title);
            return 0;
        });
        displaySortedResults(sortedResults, resultsDiv, university, categoryName);
    });

    displaySortedResults(sortedResults, resultsDiv, university, categoryName);
    updateLanguageStrings();
}

function displaySortedResults(results, resultsDiv, university, categoryName) {
    const resultsList = results.map((result, index) => `
        <div class="search-result card" data-result-id="${index}">
            <h4 class="result-title">
                <a href="${result.url}" target="_blank">${result.title}</a>
            </h4>
            <p class="result-summary">${result.content_summary || result.content.substring(0, 200)}...</p>
            <ul class="key-points">
                ${result.key_points?.map(point => `<li>${point}</li>`).join('') || '<li>No key points available</li>'}
            </ul>
            <div class="result-meta">
                <div class="keywords">
                    ${(result.matched_keywords || []).map(kw => `<span class="keyword-tag">${kw}</span>`).join('')}
                </div>
                <div class="relevance">
                    <span class="relevance-score">
                        ${translations[currentLanguage]?.relevance_score || 'Relevance'}: ${result.relevance_score.toFixed(2)}
                    </span>
                </div>
            </div>
            <div class="result-actions">
                <button class="btn action-btn ask-btn" data-title="${result.title}" data-lang-key="ask_about">${translations[currentLanguage]?.ask_about || 'Ask About This'}</button>
                <button class="btn action-btn copy-btn" data-url="${result.url}" data-lang-key="copy_url">${translations[currentLanguage]?.copy_url || 'Copy URL'}</button>
            </div>
        </div>
    `).join('');

    const existingSummary = resultsDiv.querySelector('.search-summary');
    resultsDiv.innerHTML = '';
    if (existingSummary) {
        resultsDiv.appendChild(existingSummary);
    }
    resultsDiv.innerHTML += resultsList;

    resultsDiv.querySelectorAll('.ask-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            console.log('Ask button clicked for:', btn.getAttribute('data-title'));
            const title = btn.getAttribute('data-title');
            switchMode('contract');
            const chatInput = document.getElementById('chatInput');
            chatInput.value = `Tell me more about ${title}`;
            chatInput.focus();
        });
    });

    resultsDiv.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            console.log('Copy URL button clicked:', btn.getAttribute('data-url'));
            const url = btn.getAttribute('data-url');
            navigator.clipboard.writeText(url).then(() => {
                showError(translations[currentLanguage]?.url_copied || 'URL copied to clipboard!', true);
            }).catch(err => {
                console.error('Copy URL error:', err);
                showError(translations[currentLanguage]?.copy_failed || 'Failed to copy URL.');
            });
        });
    });
}

function autoResizeTextarea() {
    const textarea = document.getElementById('chatInput');
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
}

// Modified: Use event delegation for student form submission
function setupStudentFormListener() {
    const studentSection = document.getElementById('studentSection');
    if (!studentSection) {
        console.error('Student section not found in DOM');
        return;
    }

    // Remove any existing listeners to prevent duplicates
    studentSection.removeEventListener('submit', handleStudentFormSubmit);
    studentSection.addEventListener('submit', handleStudentFormSubmit);
    console.log('Student form submit listener attached via delegation');
}

function handleStudentFormSubmit(event) {
    if (event.target.matches('#studentSearchForm')) {
        console.log('Delegated submit event triggered for studentSearchForm');
        handleStudentSearch(event);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        const form = document.getElementById('uploadForm');
        if (form) {
            form.addEventListener('submit', handleFileUpload);
            console.log('Form submit handler attached for uploadForm');
        }

        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendMessage');
        if (chatInput) {
            chatInput.addEventListener('keypress', e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    console.log('Enter key pressed in chatInput');
                    sendChatMessage();
                }
            });
            chatInput.addEventListener('input', autoResizeTextarea);
        }
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                console.log('Send message button clicked');
                sendChatMessage();
            });
        }

        const contractBtn = document.getElementById('contractModeBtn');
        const studentBtn = document.getElementById('studentModeBtn');
        if (contractBtn && studentBtn) {
            contractBtn.addEventListener('click', () => {
                console.log('Switching to contract mode');
                switchMode('contract');
            });
            studentBtn.addEventListener('click', () => {
                console.log('Switching to student mode');
                switchMode('student');
                setupStudentFormListener(); // Reattach listener on mode switch
            });
        }

        const savedMode = localStorage.getItem('currentMode') || 'contract';
        switchMode(savedMode);

        const savedLanguage = localStorage.getItem('preferredLanguage');
        if (savedLanguage) {
            currentLanguage = savedLanguage;
            document.getElementById('languageSelect').value = savedLanguage;
            updateLanguageStrings();
            updateMarksTranslations();
        }

        // Setup student form listener
        setupStudentFormListener();

        const universityInput = document.getElementById('universityInput');
        if (universityInput) {
            universityInput.addEventListener('input', () => {
                console.log('University input changed:', universityInput.value);
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(async () => {
                    const query = universityInput.value.trim();
                    if (query.length >= 3) {
                        const suggestions = await fetchUniversitySuggestions(query);
                        displaySuggestions(suggestions, 'universitySuggestions', text => {
                            universityInput.value = text;
                        });
                    } else {
                        document.getElementById('universitySuggestions').innerHTML = '';
                    }
                }, 300);
            });
        }

        const customInput = document.getElementById('customKeywords');
        if (customInput) {
            customInput.addEventListener('input', () => {
                console.log('Custom keywords input changed:', customInput.value);
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(async () => {
                    const category = document.querySelector('input[name="category"]:checked')?.value;
                    if (category === 'custom') {
                        const suggestions = await fetchKeywordSuggestions(category);
                        displaySuggestions(suggestions, 'keywordSuggestions', text => {
                            customInput.value = text;
                        });
                    }
                }, 300);
            });
        }

        const categoryInputs = document.querySelectorAll('input[name="category"]');
        categoryInputs.forEach(input => {
            input.addEventListener('change', () => {
                console.log('Category changed:', input.value);
                const customContainer = document.getElementById('customKeywordsContainer');
                customContainer.style.display = input.value === 'custom' ? 'block' : 'none';
                document.getElementById('keywordSuggestions').innerHTML = '';
            });
        });

        const languageSelect = document.getElementById('languageSelect');
        if (languageSelect) {
            languageSelect.addEventListener('change', () => {
                console.log('Language changed:', languageSelect.value);
                changeLanguage();
            });
        }

        window.addEventListener('beforeunload', endChatSession);
    } catch (error) {
        console.error('DOMContentLoaded error:', error);
    }
});