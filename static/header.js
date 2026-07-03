(function() {
    const headerHTML = `
        <header class="site-header" id="siteHeader">
            <div class="header-wrapper">
                <a href="/" class="header-logo">
                    <img src="/static/logo.jpeg" alt="Логотип" class="logo-img" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <span class="logo-fallback" style="display: none;">ВВ</span>
                    <span class="logo-text">Виртуальные визитки</span>
                </a>
                
                <button class="mobile-menu-toggle" id="mobileMenuToggle">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
                
                <nav class="header-nav" id="headerNav">
                    <div class="nav-guest" id="navGuest" style="display: none;">
                        <a href="/activate" class="nav-link">Активация</a>
                        <a href="/login" class="nav-link nav-link-primary">Войти</a>
                    </div>
                    
                    <div class="nav-user" id="navUser" style="display: none;">
                        <span class="nav-email" id="navEmail"></span>
                        <a href="/cabinet" class="nav-link">Кабинет</a>
                        <a href="/admin" class="nav-link" id="adminLink" style="display: none;">Админ</a>
                        <button class="nav-link nav-link-logout" id="navLogout">Выйти</button>
                    </div>
                </nav>
            </div>
        </header>
        <div class="header-spacer"></div>
    `;

    const headerCSS = `
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { 
            overflow-x: hidden; 
            width: 100%;
            margin: 0;
            padding: 0;
        }

        .site-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            background: white;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            border-bottom: 1px solid #e2e8f0;
            z-index: 9999;
        }

        .header-wrapper {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            height: 70px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header-logo {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: #2d3748;
        }

        .logo-img { height: 45px; width: auto; object-fit: contain; }
        .logo-fallback {
            height: 45px; width: 45px; background: #5a67d8; color: white;
            border-radius: 8px; display: flex; align-items: center;
            justify-content: center; font-weight: 700; font-size: 18px;
        }
        .logo-text { font-size: 18px; font-weight: 600; }

        .header-nav { display: flex; align-items: center; gap: 8px; }

        .nav-link {
            padding: 8px 16px; color: #4a5568; text-decoration: none;
            font-size: 14px; font-weight: 500; border-radius: 6px;
            background: none; border: none; cursor: pointer;
        }
        .nav-link:hover { color: #5a67d8; background: #f7fafc; }
        .nav-link-primary { background: #5a67d8; color: white; }
        .nav-link-logout { color: #c53030; }
        .nav-link-logout:hover { background: #fff5f5; }
        .nav-email { padding: 8px 12px; color: #718096; font-size: 13px; margin-right: 8px; }
        .header-spacer { height: 70px; }

        .mobile-menu-toggle {
            display: none; flex-direction: column; gap: 5px;
            width: 28px; height: 22px; background: none; border: none; cursor: pointer; padding: 0;
        }
        .mobile-menu-toggle span {
            display: block; height: 2px; width: 100%; background: #4a5568; border-radius: 2px;
        }

        @media screen and (max-width: 768px) {
            .mobile-menu-toggle { display: flex; }
            .header-wrapper { height: 60px; padding: 0 15px; }
            .header-spacer { height: 60px; }
            .logo-img { height: 38px; }
            .logo-fallback { height: 38px; width: 38px; }
            .logo-text { font-size: 16px; }

            .header-nav {
                position: fixed; top: 60px; left: 0; right: 0; width: 100%;
                background: white; flex-direction: column; padding: 20px; gap: 8px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08); border-bottom: 1px solid #e2e8f0;
                transform: translateY(-120%); transition: transform 0.3s; z-index: 9998;
            }
            .header-nav.open { transform: translateY(0); }
            .nav-link { padding: 12px 16px; text-align: center; }
        }

        @media screen and (max-width: 380px) {
            .logo-text { display: none; }
            .logo-img { height: 40px; }
        }
    `;

    const styleEl = document.createElement('style');
    styleEl.textContent = headerCSS;
    document.head.appendChild(styleEl);

    document.body.insertAdjacentHTML('afterbegin', headerHTML);
    document.body.style.margin = '0';
    document.body.style.padding = '0';

    async function checkAuth() {
        try {
            const response = await fetch('/api/check-auth');
            const data = await response.json();
            
            const navGuest = document.getElementById('navGuest');
            const navUser = document.getElementById('navUser');
            const navEmail = document.getElementById('navEmail');
            const adminLink = document.getElementById('adminLink');
            
            if (data.authenticated) {
                navGuest.style.display = 'none';
                navUser.style.display = 'flex';
                navUser.style.alignItems = 'center';
                navEmail.textContent = data.email;
                
                try {
                    const adminResponse = await fetch('/api/admin/check');
                    const adminData = await adminResponse.json();
                    if (adminData.is_admin && adminLink) {
                        adminLink.style.display = 'inline-block';
                    }
                } catch (e) {}
            } else {
                navGuest.style.display = 'flex';
                navUser.style.display = 'none';
            }
        } catch (error) {}
    }

    const toggleBtn = document.getElementById('mobileMenuToggle');
    const nav = document.getElementById('headerNav');
    
    toggleBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        nav.classList.toggle('open');
    });

    nav.addEventListener('click', function(e) {
        if (e.target.tagName === 'A') {
            nav.classList.remove('open');
        }
    });

    const logoutBtn = document.getElementById('navLogout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function() {
            try {
                await fetch('/api/logout', { method: 'POST' });
                window.location.href = '/login';
            } catch (error) {
                window.location.href = '/login';
            }
        });
    }

    checkAuth();
})();
