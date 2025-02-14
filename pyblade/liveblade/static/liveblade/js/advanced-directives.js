// // Advanced Directives for LiveBlade

// // Loading Directive
// directive('loading', ({ el, component }) => {
//     // Initial state
//     el.style.display = 'none';
    
//     // Listen to loading events
//     document.addEventListener('request.start', () => {
//         el.style.display = 'block';
//     });
    
//     document.addEventListener('request.end', () => {
//         el.style.display = 'none';
//     });

//     // Optional loading states for specific actions
//     if (el.hasAttribute('b-loading.for')) {
//         const targetId = el.getAttribute('b-loading.for');
//         const target = document.getElementById(targetId);
        
//         if (target) {
//             target.addEventListener('loading.start', () => {
//                 el.style.display = 'block';
//             });
            
//             target.addEventListener('loading.end', () => {
//                 el.style.display = 'none';
//             });
//         }
//     }
// });

// // Error Directive
// directive('error', ({ el, component }) => {
//     // Initial setup
//     el.style.display = 'none';
//     let errorMessage = el.innerHTML;
//     let timeout;

//     // Function to show error
//     const showError = (message) => {
//         el.textContent = message || errorMessage;
//         el.style.display = 'block';
        
//         // Auto-hide after 5 seconds if the modifier is present
//         if (el.hasAttribute('b-error.auto-hide')) {
//             if (timeout) clearTimeout(timeout);
//             timeout = setTimeout(() => {
//                 el.style.display = 'none';
//             }, 5000);
//         }
//     };

//     // Listen to error events
//     document.addEventListener('blade.error', (event) => {
//         showError(event.detail.message);
//     });

//     // Clear error on success if specified
//     if (el.hasAttribute('b-error.clear-on-success')) {
//         document.addEventListener('request.end', () => {
//             el.style.display = 'none';
//         });
//     }
// });

// // Lazy Loading Directive
// directive('lazy', ({ el, component, directive }) => {
//     const options = {
//         root: null,
//         rootMargin: '50px',
//         threshold: 0.1
//     };

//     const loadComponent = async () => {
//         try {
//             const componentName = directive.expression;
            
//             // Show loading state
//             el.innerHTML = '<div class="blade-lazy-loading">Loading...</div>';
            
//             // Call server to get component content
//             const response = await fetch('/', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                     'X-CSRFToken': getCookie('csrftoken')
//                 },
//                 body: JSON.stringify({
//                     component: componentName,
//                     method: 'render',
//                     lazy: true
//                 })
//             });

//             const data = await response.json();
            
//             if (data.html) {
//                 el.innerHTML = data.html;
//                 // Initialize the loaded component
//                 initializeComponent(el);
//             }
//         } catch (error) {
//             el.innerHTML = '<div class="blade-lazy-error">Failed to load component</div>';
//             emit('blade.error', { message: 'Failed to load lazy component' });
//         }
//     };

//     // Create intersection observer
//     const observer = new IntersectionObserver((entries) => {
//         entries.forEach(entry => {
//             if (entry.isIntersecting) {
//                 loadComponent();
//                 observer.unobserve(el);
//             }
//         });
//     }, options);

//     // Start observing
//     observer.observe(el);
// });
