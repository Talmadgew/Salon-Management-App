async function loadServices() {
  const response = await fetch('/api/services');
  return response.json();
}

function buildCheckItem(name, label, checked = false) {
  const wrapper = document.createElement('label');
  wrapper.className = 'check-item';
  const input = document.createElement('input');
  input.type = 'checkbox';
  input.name = name;
  input.checked = checked;
  const span = document.createElement('span');
  span.textContent = label;
  wrapper.appendChild(input);
  wrapper.appendChild(span);
  return wrapper;
}

async function initRecordForm() {
  const form = document.getElementById('recordForm');
  if (!form) return;
  const { services, common_acknowledgements } = await loadServices();
  const serviceCode = document.getElementById('serviceCode');
  const intakeWrap = document.getElementById('intakeQuestions');
  const ackWrap = document.getElementById('serviceAcknowledgements');
  const commonWrap = document.getElementById('commonAcknowledgements');
  const sunbedExtras = document.getElementById('sunbedExtras');
  const payload = window.initialPayload || {};

  function renderService() {
    const code = serviceCode.value;
    intakeWrap.innerHTML = '';
    ackWrap.innerHTML = '';
    commonWrap.innerHTML = '';
    if (!services[code]) {
      sunbedExtras.classList.add('hidden');
      return;
    }
    sunbedExtras.classList.toggle('hidden', code !== 'sunbed');
    services[code].intake.forEach((item, idx) => {
      intakeWrap.appendChild(buildCheckItem(`intake_${idx}`, item, Boolean(payload[`intake_${idx}`])));
    });
    services[code].acknowledgements.forEach((item, idx) => {
      ackWrap.appendChild(buildCheckItem(`service_ack_${idx}`, item, Boolean(payload[`service_ack_${idx}`])));
    });
    common_acknowledgements.forEach((item, idx) => {
      commonWrap.appendChild(buildCheckItem(`common_ack_${idx}`, item, Boolean(payload[`common_ack_${idx}`])));
    });
  }

  serviceCode.addEventListener('change', renderService);
  renderService();
  initSignaturePad();
}

function initSignaturePad() {
  const canvas = document.getElementById('signaturePad');
  if (!canvas) return;
  const hidden = document.getElementById('signatureData');
  const clearBtn = document.getElementById('clearSignature');
  const ctx = canvas.getContext('2d');
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  let drawing = false;

  function pos(event) {
    const rect = canvas.getBoundingClientRect();
    const source = event.touches ? event.touches[0] : event;
    return {
      x: (source.clientX - rect.left) * (canvas.width / rect.width),
      y: (source.clientY - rect.top) * (canvas.height / rect.height),
    };
  }
  function start(event) {
    drawing = true;
    const p = pos(event);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    event.preventDefault();
  }
  function move(event) {
    if (!drawing) return;
    const p = pos(event);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    hidden.value = canvas.toDataURL('image/png');
    event.preventDefault();
  }
  function end() {
    drawing = false;
    hidden.value = canvas.toDataURL('image/png');
  }
  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', move);
  window.addEventListener('mouseup', end);
  canvas.addEventListener('touchstart', start, { passive: false });
  canvas.addEventListener('touchmove', move, { passive: false });
  canvas.addEventListener('touchend', end);
  clearBtn?.addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    hidden.value = '';
  });
}

function initBookingForm() {
  const form = document.getElementById('bookingForm');
  if (!form) return;
  const service = document.getElementById('bookingService');
  const duration = document.getElementById('bookingDuration');
  const price = document.getElementById('bookingPrice');
  service?.addEventListener('change', () => {
    const opt = service.options[service.selectedIndex];
    if (!duration.value && opt.dataset.duration) duration.value = opt.dataset.duration;
    if (!price.value && opt.dataset.price) price.value = opt.dataset.price;
  });
}

function makeLine(idx, line = {}) {
  const wrap = document.createElement('div');
  wrap.className = 'invoice-line';
  wrap.innerHTML = `
    <label>Type
      <select name="line_item_type_${idx}" class="line-type">
        <option value="service" ${line.item_type === 'service' ? 'selected' : ''}>Service</option>
        <option value="product" ${line.item_type === 'product' ? 'selected' : ''}>Product</option>
        <option value="manual" ${!line.item_type || line.item_type === 'manual' ? 'selected' : ''}>Manual</option>
      </select>
    </label>
    <label>Description<input name="line_description_${idx}" value="${line.description || ''}" required /></label>
    <label>Service
      <select name="line_service_code_${idx}" class="line-service"><option value="">None</option></select>
    </label>
    <label>Product
      <select name="line_product_id_${idx}" class="line-product"><option value="">None</option></select>
    </label>
    <label>Qty<input type="number" min="0.01" step="0.01" name="line_qty_${idx}" value="${line.qty || 1}" /></label>
    <label>Price<input type="number" min="0" step="0.01" name="line_price_${idx}" value="${line.unit_price || 0}" /></label>
    <button type="button" class="secondary remove-line">Remove</button>
  `;
  const serviceSelect = wrap.querySelector('.line-service');
  Object.entries(window.invoiceServices || {}).forEach(([code, svc]) => {
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = svc.name;
    opt.dataset.price = svc.default_price;
    if (line.service_code === code) opt.selected = true;
    serviceSelect.appendChild(opt);
  });
  const productSelect = wrap.querySelector('.line-product');
  (window.invoiceProducts || []).forEach((product) => {
    const opt = document.createElement('option');
    opt.value = product.id;
    opt.textContent = `${product.name} (${product.stock_qty} in stock)`;
    opt.dataset.price = product.unit_price;
    if (String(line.product_id || '') === String(product.id)) opt.selected = true;
    productSelect.appendChild(opt);
  });

  wrap.querySelector('.remove-line').addEventListener('click', () => wrap.remove());
  serviceSelect.addEventListener('change', () => {
    const opt = serviceSelect.options[serviceSelect.selectedIndex];
    if (opt.value) {
      wrap.querySelector(`[name="line_description_${idx}"]`).value = opt.text;
      wrap.querySelector(`[name="line_price_${idx}"]`).value = opt.dataset.price || 0;
      wrap.querySelector('.line-type').value = 'service';
    }
  });
  productSelect.addEventListener('change', () => {
    const opt = productSelect.options[productSelect.selectedIndex];
    if (opt.value) {
      wrap.querySelector(`[name="line_description_${idx}"]`).value = opt.text.split(' (')[0];
      wrap.querySelector(`[name="line_price_${idx}"]`).value = opt.dataset.price || 0;
      wrap.querySelector('.line-type').value = 'product';
    }
  });
  return wrap;
}

function initInvoiceForm() {
  const container = document.getElementById('invoiceLines');
  const btn = document.getElementById('addInvoiceLine');
  if (!container || !btn) return;
  let idx = 0;
  function add(line) {
    container.appendChild(makeLine(idx, line));
    idx += 1;
  }
  const initial = window.invoiceInitialLines || [];
  if (initial.length) initial.forEach(add);
  else add({ item_type: 'service', qty: 1, unit_price: 0 });
  btn.addEventListener('click', () => add({ item_type: 'manual', qty: 1, unit_price: 0 }));
}

document.addEventListener('DOMContentLoaded', () => {
  initRecordForm();
  initBookingForm();
  initInvoiceForm();
});
