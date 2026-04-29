import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Customers from './pages/Customers';
import Invoices from './pages/Invoices';
import WhatsApp from './pages/WhatsApp';
import Gmail from './pages/Gmail';
import SocialMediaHub from './pages/SocialMediaHub';
import { fetchHealth } from './services/api';

export default function App() {
  const [connected, setConnected] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then(data => setConnected(data.status === 'connected'))
      .catch(() => setConnected(false));
  }, []);

  return (
    <BrowserRouter>
      {/* Root flex container — sidebar + main side by side, never overlap */}
      <div className="flex min-h-screen" style={{ background: '#030712' }}>
        {/* Sidebar: fixed width, no position:fixed, part of flex flow */}
        <Sidebar connected={connected} collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />

        {/* Main content: flex-1 takes remaining space */}
        <main
          className="flex-1 min-w-0 p-8 pb-12 overflow-y-auto transition-all duration-300"
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/invoices" element={<Invoices />} />
            <Route path="/whatsapp" element={<WhatsApp />} />
            <Route path="/gmail" element={<Gmail />} />
            <Route path="/social" element={<SocialMediaHub />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
