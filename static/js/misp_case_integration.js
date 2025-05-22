/**
 * SentinelIQ MISP-Case Integration
 * JavaScript functions for integrating MISP threat intelligence with cases
 */

/**
 * Check if an observable has matching threat intelligence
 * 
 * @param {number} observableId - The ID of the observable to check
 * @param {string} csrfToken - The CSRF token for API calls
 */
function checkThreatIntelligenceMatch(observableId, csrfToken) {
    // Show loading indicator
    const resultDiv = document.getElementById('threat-intel-results');
    if (resultDiv) {
        resultDiv.innerHTML = '<div class="text-center p-4"><i class="fas fa-circle-notch fa-spin fa-2x mb-3"></i><p>Checking threat intelligence feeds...</p></div>';
    }
    
    // Make API call to check for matches
    fetch(`/vision/threat-intel-match/${observableId}/`, {
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Found matches
            if (data.count > 0) {
                displayThreatIntelMatches(data.matches, resultDiv);
            } else {
                // No matches found
                resultDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-info-circle me-2"></i>No threat intelligence matches found for this observable.</div>';
            }
        } else {
            // Error occurred
            resultDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>${data.error || 'An error occurred while checking threat intelligence.'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error checking threat intel:', error);
        resultDiv.innerHTML = '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>Error connecting to the server. Please try again.</div>';
    });
}

/**
 * Display threat intelligence matches in the result container
 * 
 * @param {Array} matches - The list of threat intelligence matches
 * @param {HTMLElement} container - The container element to display results in
 */
function displayThreatIntelMatches(matches, container) {
    // Clear the container
    container.innerHTML = '';
    
    // Create a header
    const header = document.createElement('div');
    header.className = 'alert alert-success';
    header.innerHTML = `<i class="fas fa-check-circle me-2"></i>Found ${matches.length} threat intelligence match${matches.length !== 1 ? 'es' : ''}!`;
    container.appendChild(header);
    
    // Create a card for each match
    matches.forEach(match => {
        const card = document.createElement('div');
        card.className = 'card mb-3 border-info';
        
        // Create card header
        const cardHeader = document.createElement('div');
        cardHeader.className = 'card-header bg-light d-flex justify-content-between align-items-center';
        cardHeader.innerHTML = `
            <div>
                <span class="badge bg-secondary me-2">${match.type}</span>
                <strong>${match.value}</strong>
            </div>
            <div>
                ${match.is_malicious ? '<span class="badge bg-danger ms-2">Malicious</span>' : ''}
                <span class="badge ${getTLPBadgeClass(match.tlp)} ms-1">TLP:${match.tlp.toUpperCase()}</span>
            </div>
        `;
        card.appendChild(cardHeader);
        
        // Create card body
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        // Add source info
        const sourceInfo = document.createElement('p');
        sourceInfo.className = 'mb-2';
        sourceInfo.innerHTML = `<strong>Source:</strong> ${match.feed_name}`;
        if (match.creator_org) {
            sourceInfo.innerHTML += ` <span class="text-muted">(${match.creator_org})</span>`;
        }
        cardBody.appendChild(sourceInfo);
        
        // Add confidence
        const confidence = document.createElement('p');
        confidence.className = 'mb-2';
        confidence.innerHTML = `<strong>Confidence:</strong> <span class="badge ${getConfidenceBadgeClass(match.confidence)}">${match.confidence}</span>`;
        cardBody.appendChild(confidence);
        
        // Add tags if available
        if (match.tags && match.tags.length > 0) {
            const tagsDiv = document.createElement('div');
            tagsDiv.className = 'mb-2';
            tagsDiv.innerHTML = '<strong>Tags:</strong> ';
            
            const tagsList = document.createElement('div');
            tagsList.className = 'mt-1';
            
            match.tags.split(',').forEach(tag => {
                const tagBadge = document.createElement('span');
                tagBadge.className = 'badge bg-info me-1 mb-1';
                tagBadge.textContent = tag.trim();
                tagsList.appendChild(tagBadge);
            });
            
            tagsDiv.appendChild(tagsList);
            cardBody.appendChild(tagsDiv);
        }
        
        // Add description if available
        if (match.description) {
            const description = document.createElement('div');
            description.className = 'mt-3';
            description.innerHTML = `<strong>Description:</strong><p class="text-muted mt-1">${match.description}</p>`;
            cardBody.appendChild(description);
        }
        
        card.appendChild(cardBody);
        
        // Add card footer with link
        if (match.external_url) {
            const cardFooter = document.createElement('div');
            cardFooter.className = 'card-footer bg-light';
            cardFooter.innerHTML = `<a href="${match.external_url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-primary"><i class="fas fa-external-link-alt me-1"></i> View in Source</a>`;
            card.appendChild(cardFooter);
        }
        
        container.appendChild(card);
    });
}

/**
 * Get the appropriate Bootstrap badge class for a TLP level
 * 
 * @param {string} tlp - The TLP level (white, green, amber, red)
 * @returns {string} The Bootstrap badge class
 */
function getTLPBadgeClass(tlp) {
    switch (tlp.toLowerCase()) {
        case 'white': return 'bg-light text-dark';
        case 'green': return 'bg-success';
        case 'amber': return 'bg-warning text-dark';
        case 'red': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

/**
 * Get the appropriate Bootstrap badge class for a confidence level
 * 
 * @param {string} confidence - The confidence level (low, medium, high)
 * @returns {string} The Bootstrap badge class
 */
function getConfidenceBadgeClass(confidence) {
    switch (confidence.toLowerCase()) {
        case 'low': return 'bg-secondary';
        case 'medium': return 'bg-info text-dark';
        case 'high': return 'bg-success';
        default: return 'bg-secondary';
    }
} 