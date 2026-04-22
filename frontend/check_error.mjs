fetch('http://localhost:3000')
  .then(r => r.text())
  .then(html => {
    // Look for Next.js error content
    const errMatch = html.match(/__next_error__[^>]*>([^<]+)/);
    if (errMatch) console.log('Next Error:', errMatch[1]);
    
    // Print a chunk around any "error" mention
    const lower = html.toLowerCase();
    const idx = lower.indexOf('error');
    if (idx > -1) {
      console.log('Error context:', html.substring(Math.max(0, idx - 100), idx + 300));
    }
    
    // Also check for the digest
    const digestMatch = html.match(/"digest":"([^"]+)"/);
    if (digestMatch) console.log('Digest:', digestMatch[1]);
    
    console.log('HTML length:', html.length);
    console.log('First 500:', html.substring(0, 500));
  })
  .catch(e => console.error('Fetch failed:', e.message));
