// Main JavaScript file for SentinelIQ application with Carbon Design System

document.addEventListener('DOMContentLoaded', function() {
    console.log('SentinelIQ application initialized with Carbon Design System');

    // Initialize Carbon components if needed
    if (typeof CarbonComponents !== 'undefined') {
        // Example: Initialize a specific component if needed
        // const dropdown = document.querySelector('.bx--dropdown');
        // if (dropdown) {
        //     CarbonComponents.Dropdown.create(dropdown);
        // }
    }

    // Add any custom JavaScript functionality here

    // Example of handling Carbon modal
    const modalButtons = document.querySelectorAll('[data-modal-target]');
    modalButtons.forEach(button => {
        button.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal-target');
            const modal = document.getElementById(modalId);
            if (modal && typeof CarbonComponents !== 'undefined') {
                CarbonComponents.Modal.create(modal);
            }
        });
    });
});
