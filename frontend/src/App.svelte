 <script>
  import { onMount } from 'svelte';
  import { fade, slide, scale } from 'svelte/transition';
  import { flip } from 'svelte/animate';

  // ── Auth (token armazenado apenas em memória) ──────────────────────────────
  let token = null;
  let loginUsername = '';
  let loginPassword = '';
  let loginErro = '';
  let loginCarregando = false;

  function authHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  }

  async function fazerLogin() {
    loginErro = '';
    loginCarregando = true;
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUsername, password: loginPassword }),
      });
      if (res.ok) {
        const dados = await res.json();
        token = dados.access_token;
        loginUsername = '';
        loginPassword = '';
        await carregarPedidos();
      } else {
        loginErro = 'Usuário ou senha inválidos.';
      }
    } catch {
      loginErro = 'Erro de conexão com o servidor.';
    } finally {
      loginCarregando = false;
    }
  }

  function sair() {
    token = null;
    listaPedidos = [];
  }

  // ── Estados da aplicação ───────────────────────────────────────────────────
  let item = '', quantidade = 1, urgencia = 'Normal', preco_estimado = '', setor = 'TI';
  let busca = '';
  let filtroStatus = 'Todos';
  let mostrarPendentes = true;
  let mostrarComprados = true;
  let listaPedidos = [];
  let enviando = false;

  // Processamento de dados
  $: pedidosFiltrados = listaPedidos.filter(p => {
    const matchBusca = p.item.toLowerCase().includes(busca.toLowerCase()) || p.setor.toLowerCase().includes(busca.toLowerCase());
    const matchStatus = filtroStatus === 'Todos' ? true : (filtroStatus === 'Pendentes' ? !p.comprado : p.comprado);
    return matchBusca && matchStatus;
  });

  $: pendentes = pedidosFiltrados.filter(p => !p.comprado);
  $: comprados = pedidosFiltrados.filter(p => p.comprado);

  $: totalPendente = listaPedidos.filter(p => !p.comprado).reduce((acc, p) => acc + (p.quantidade * p.preco_estimado), 0);

  async function carregarPedidos() {
    try {
      const res = await fetch('/pedidos', { headers: authHeaders() });
      if (res.status === 401) { sair(); return; }
      listaPedidos = await res.json();
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
    }
  }

  async function enviarPedido() {
    if (!item) return;
    enviando = true;
    try {
      const res = await fetch('/pedidos', {
        method: 'POST',
        body: JSON.stringify({ item, quantidade, urgencia, preco_estimado: parseFloat(preco_estimado) || 0, setor, comprado: false }),
        headers: authHeaders(),
      });
      if (res.status === 401) { sair(); return; }
      if (res.ok) {
        await carregarPedidos();
        item = ''; preco_estimado = '';
      }
    } finally {
      enviando = false;
    }
  }

  async function marcarComprado(id) {
    const res = await fetch(`/pedidos/${id}/concluir`, { method: 'PUT', headers: authHeaders() });
    if (res.status === 401) { sair(); return; }
    carregarPedidos();
  }

  async function deletar(id) {
    const res = await fetch(`/pedidos/${id}`, { method: 'DELETE', headers: authHeaders() });
    if (res.status === 401) { sair(); return; }
    carregarPedidos();
  }

  function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(valor);
  }

  function formatarData(dataIso) {
    if (!dataIso) return '-';
    const [ano, mes, dia] = dataIso.split('-');
    return `${dia}/${mes}/${ano}`;
  }
</script>

{#if !token}
  <!-- ── Tela de Login ─────────────────────────────────────────────────── -->
  <div class="login-overlay" transition:fade>
    <div class="login-card">
      <div class="login-logo">
        <h1>Gestão de Suprimentos <span class="badge-pro">PRO</span></h1>
        <p>Faça login para continuar</p>
      </div>

      <label for="loginUser">Usuário</label>
      <input
        id="loginUser"
        type="text"
        bind:value={loginUsername}
        placeholder="admin"
        on:keydown={(e) => e.key === 'Enter' && fazerLogin()}
      />

      <label for="loginPass">Senha</label>
      <input
        id="loginPass"
        type="password"
        bind:value={loginPassword}
        placeholder="••••••••"
        on:keydown={(e) => e.key === 'Enter' && fazerLogin()}
      />

      {#if loginErro}
        <p class="login-erro" transition:fade>{loginErro}</p>
      {/if}

      <button class="btn-login" on:click={fazerLogin} disabled={loginCarregando || !loginUsername || !loginPassword}>
        {loginCarregando ? 'Entrando...' : 'Entrar'}
      </button>
    </div>
  </div>

{:else}
  <!-- ── Aplicação principal ───────────────────────────────────────────── -->
  <main transition:fade>
    <header>
      <div class="logo-area">
        <div>
          <h1 class="logo-text">Gestão de Suprimentos <span class="badge-pro">PRO</span></h1>
          <p class="subtitle">Painel de Controle e Aprovações</p>
        </div>
      </div>
      <div class="header-right">
        <div class="kpi-main">
          <span class="kpi-label">Orçamento em Fila</span>
          <strong class="kpi-value">{formatarMoeda(totalPendente)}</strong>
        </div>
        <button class="btn-sair" on:click={sair}>Sair</button>
      </div>
    </header>

    <div class="tool-bar">
      <div class="search-wrapper">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="text" bind:value={busca} placeholder="Pesquisar registro..." class="search-input" />
      </div>
      <div class="filter-wrapper">
        <label for="filtroSelect">Visualização:</label>
        <select id="filtroSelect" bind:value={filtroStatus}>
          <option value="Todos">Visão Geral</option>
          <option value="Pendentes">Apenas Fila de Suprimentos</option>
          <option value="Comprados">Apenas Histórico Finalizado</option>
        </select>
      </div>
    </div>

    <div class="main-layout">

      <aside class="sidebar">
        <div class="card-form">
          <h3>Novo Registro</h3>

          <label for="inputItem">Descrição do Item</label>
          <input id="inputItem" type="text" bind:value={item} placeholder="Servidor, Monitor..." />

          <div class="row">
            <div class="col">
              <label for="inputQtd">Quantidade</label>
              <input id="inputQtd" type="number" bind:value={quantidade} min="1"/>
            </div>
            <div class="col">
              <label for="inputPreco">Preço Unitário (R$)</label>
              <input id="inputPreco" type="number" bind:value={preco_estimado} min="0"/>
            </div>
          </div>

          <label for="inputSetor">Centro de Custo (Setor)</label>
          <select id="inputSetor" bind:value={setor}>
              <option>TI</option><option>RH</option><option>Vendas</option><option>Marketing</option><option>Diretoria</option>
          </select>

          <span class="fake-label">Prioridade</span>
          <div class="urgencia-group">
            {#each ['Baixa', 'Normal', 'Alta'] as nivel}
              <button class="btn-urgencia {urgencia === nivel ? 'active' : ''}" on:click={() => urgencia = nivel}>{nivel}</button>
            {/each}
          </div>

          <button class="btn-submit" on:click={enviarPedido} disabled={enviando || !item}>
            {enviando ? 'Processando...' : 'Adicionar ao Sistema'}
          </button>
        </div>
      </aside>

      <section class="content-area">

        {#if filtroStatus === 'Todos' || filtroStatus === 'Pendentes'}
          <div class="section-container">
            <button class="section-header" on:click={() => mostrarPendentes = !mostrarPendentes}>
              <h2>Fila de Suprimentos <span class="counter">{pendentes.length}</span></h2>
              <svg class="toggle-icon {mostrarPendentes ? '' : 'rotated'}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </button>

            {#if mostrarPendentes}
              <div class="grid-cards" transition:slide={{duration: 300}}>
                {#each pendentes as p (p.id)}
                  <div animate:flip={{duration: 300}} transition:scale={{duration: 200}} class="card {p.urgencia.toLowerCase()}">
                    <div class="card-header">
                      <span class="setor-tag">{p.setor}</span>
                      <span class="date-tag">Data: {formatarData(p.data_criacao)}</span>
                    </div>
                    <h4 class="item-title">{p.item}</h4>
                    <p class="item-details">
                      <span>Qtd: <strong>{p.quantidade}</strong></span>
                      <span class="divider">|</span>
                      <span>Total: <strong>{formatarMoeda(p.quantidade * p.preco_estimado)}</strong></span>
                    </p>
                    <div class="card-actions">
                      <button class="btn-action check" on:click={() => marcarComprado(p.id)}>Finalizar</button>
                      <button class="btn-action del" on:click={() => deletar(p.id)}>Excluir</button>
                    </div>
                  </div>
                {:else}
                  <div class="empty-state">Nenhum registro pendente no sistema.</div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}

        {#if filtroStatus === 'Todos' || filtroStatus === 'Comprados'}
          <div class="section-container mt-4">
            <button class="section-header header-comprados" on:click={() => mostrarComprados = !mostrarComprados}>
              <h2>Histórico Finalizado <span class="counter">{comprados.length}</span></h2>
              <svg class="toggle-icon {mostrarComprados ? '' : 'rotated'}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </button>

            {#if mostrarComprados}
              <div class="grid-cards" transition:slide={{duration: 300}}>
                {#each comprados as p (p.id)}
                  <div animate:flip={{duration: 300}} transition:scale={{duration: 200}} class="card done">
                    <div class="card-header">
                      <span class="setor-tag">{p.setor}</span>
                      <span class="date-tag">Data: {formatarData(p.data_criacao)}</span>
                    </div>
                    <h4 class="item-title strikethrough">{p.item}</h4>
                    <p class="item-details">
                      <span>Qtd: <strong>{p.quantidade}</strong></span>
                      <span class="divider">|</span>
                      <span>Custo: <strong>{formatarMoeda(p.quantidade * p.preco_estimado)}</strong></span>
                    </p>
                    <div class="card-actions only-delete">
                      <span class="status-badge">Concluído</span>
                      <button class="btn-action del-sm" on:click={() => deletar(p.id)}>Remover Registro</button>
                    </div>
                  </div>
                {:else}
                  <div class="empty-state">Nenhum histórico disponível.</div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}

      </section>
    </div>
  </main>
{/if}

<style>
  :root {
    --bg-page: #000000;
    --bg-card: #ffffff;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --danger: #ef4444;
    --success: #10b981;
    --warning: #f59e0b;
    --radius: 8px;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  }

  :global(body) { background: var(--bg-page); margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: var(--text-main); }

  /* ── Login ───────────────────────────────────────────────────────────── */
  .login-overlay {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
  }
  .login-card {
    background: var(--bg-card);
    border-radius: 12px;
    padding: 40px;
    width: 100%;
    max-width: 380px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .login-logo { margin-bottom: 16px; }
  .login-logo h1 { margin: 0 0 6px 0; font-size: 1.3rem; font-weight: 700; color: #0f172a; }
  .login-logo p { margin: 0; font-size: 0.9rem; color: var(--text-muted); }
  .login-card label { font-size: 0.8rem; font-weight: 600; color: #475569; margin-top: 10px; }
  .login-card input {
    padding: 10px 12px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    font-size: 0.95rem;
    background: #f8fafc;
    transition: 0.2s;
    outline: none;
  }
  .login-card input:focus { border-color: var(--primary); background: #fff; }
  .login-erro { color: var(--danger); font-size: 0.85rem; margin: 4px 0; }
  .btn-login {
    margin-top: 20px;
    padding: 12px;
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: 0.2s;
  }
  .btn-login:hover:not(:disabled) { background: var(--primary-hover); }
  .btn-login:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── App principal ───────────────────────────────────────────────────── */
  main { max-width: 1200px; margin: 0 auto; padding: 20px; box-sizing: border-box; }

  header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; margin-bottom: 30px; gap: 15px; }
  .logo-area { display: flex; align-items: center; gap: 15px; }
  .logo-text { margin: 0; font-size: 1.5rem; font-weight: 700; color: #0f172a; }
  .subtitle { margin: 0; font-size: 0.9rem; color: var(--text-muted); }
  .badge-pro { font-size: 0.65rem; background: #0f172a; color: #fff; padding: 3px 8px; border-radius: 4px; vertical-align: super; }

  .header-right { display: flex; align-items: center; gap: 15px; }
  .kpi-main { background: var(--bg-card); padding: 15px 25px; border-radius: var(--radius); box-shadow: var(--shadow-sm); display: flex; flex-direction: column; align-items: flex-end; border: 1px solid var(--border-color); }
  .kpi-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
  .kpi-value { font-size: 1.6rem; font-weight: 700; color: var(--primary); }

  .btn-sair {
    padding: 10px 18px;
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: 0.2s;
    white-space: nowrap;
  }
  .btn-sair:hover { color: var(--danger); border-color: var(--danger); }

  .tool-bar { display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 25px; background: var(--bg-card); padding: 15px; border-radius: var(--radius); box-shadow: var(--shadow-sm); border: 1px solid var(--border-color); align-items: center; }
  .search-wrapper { flex: 1; min-width: 250px; display: flex; align-items: center; position: relative; }
  .search-icon { position: absolute; left: 12px; }
  .search-input { width: 100%; padding: 12px 12px 12px 40px; border-radius: var(--radius); border: 1px solid var(--border-color); font-size: 0.95rem; box-sizing: border-box; outline: none; transition: border 0.2s; }
  .search-input:focus { border-color: var(--primary); }

  .filter-wrapper { display: flex; align-items: center; gap: 10px; font-size: 0.9rem; font-weight: 600; color: var(--text-muted); }
  .filter-wrapper select { padding: 10px; border-radius: var(--radius); border: 1px solid var(--border-color); outline: none; background: #fff; cursor: pointer; }

  .main-layout { display: grid; grid-template-columns: 320px 1fr; gap: 30px; align-items: start; }

  .card-form { background: var(--bg-card); padding: 25px; border-radius: var(--radius); box-shadow: var(--shadow-md); border: 1px solid var(--border-color); position: sticky; top: 20px; }
  .card-form h3 { margin-top: 0; margin-bottom: 20px; font-size: 1.1rem; color: #0f172a; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; }
  .card-form label, .fake-label { display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 6px; color: #475569; }
  .card-form input, .card-form select { width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid var(--border-color); border-radius: var(--radius); box-sizing: border-box; background: #f8fafc; transition: 0.2s; font-size: 0.9rem; }
  .card-form input:focus, .card-form select:focus { border-color: var(--primary); background: #fff; outline: none; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }

  .urgencia-group { display: flex; gap: 8px; margin-bottom: 25px; }
  .btn-urgencia { flex: 1; padding: 10px; border: 1px solid var(--border-color); background: var(--bg-page); border-radius: var(--radius); cursor: pointer; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); transition: 0.2s; }
  .btn-urgencia.active { background: #0f172a; color: #fff; border-color: #0f172a; }

  .btn-submit { width: 100%; padding: 12px; background: var(--primary); color: #fff; border: none; border-radius: var(--radius); font-weight: 600; cursor: pointer; font-size: 0.95rem; transition: 0.2s; }
  .btn-submit:hover:not(:disabled) { background: var(--primary-hover); }
  .btn-submit:disabled { opacity: 0.7; cursor: not-allowed; }

  .section-container { background: transparent; }
  .mt-4 { margin-top: 2rem; }
  .section-header { width: 100%; display: flex; justify-content: space-between; align-items: center; background: var(--bg-card); border: 1px solid var(--border-color); padding: 15px 20px; border-radius: var(--radius); cursor: pointer; transition: 0.2s; margin-bottom: 15px; box-shadow: var(--shadow-sm); }
  .section-header:hover { background: #f1f5f9; }
  .section-header h2 { margin: 0; font-size: 1.05rem; color: #0f172a; display: flex; align-items: center; gap: 10px; }
  .header-comprados h2 { color: var(--text-main); }
  .counter { background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
  .toggle-icon { transition: transform 0.3s; color: var(--text-muted); }
  .toggle-icon.rotated { transform: rotate(-90deg); }

  .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
  .card { background: var(--bg-card); padding: 18px; border-radius: var(--radius); border: 1px solid var(--border-color); border-top: 3px solid var(--border-color); box-shadow: var(--shadow-sm); display: flex; flex-direction: column; }

  .card.alta { border-top-color: var(--danger); }
  .card.normal { border-top-color: var(--warning); }
  .card.baixa { border-top-color: var(--success); }

  .card-header { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); }
  .setor-tag { background: #f1f5f9; padding: 4px 8px; border-radius: 4px; text-transform: uppercase; border: 1px solid #e2e8f0; }
  .date-tag { color: #94a3b8; }

  .item-title { margin: 0 0 10px 0; font-size: 1rem; color: var(--text-main); line-height: 1.3; }
  .strikethrough { text-decoration: line-through; color: #94a3b8; }

  .item-details { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 0.85rem; color: #475569; margin: 0 0 20px 0; background: #f8fafc; padding: 8px; border-radius: 4px; border: 1px solid #f1f5f9; }
  .divider { color: #cbd5e1; }

  .card-actions { display: flex; gap: 10px; margin-top: auto; }
  .only-delete { justify-content: space-between; align-items: center; }
  .status-badge { font-size: 0.75rem; font-weight: 600; color: var(--success); background: #f0fdf4; border: 1px solid #bbf7d0; padding: 4px 10px; border-radius: 12px; }

  .btn-action { flex: 1; padding: 8px; border: none; border-radius: 6px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: 0.2s; display: flex; justify-content: center; align-items: center; }
  .check { background: #f8fafc; color: var(--text-main); border: 1px solid var(--border-color); }
  .check:hover { background: var(--success); color: #fff; border-color: var(--success); }
  .del { flex: 0.4; background: #fff; color: var(--danger); border: 1px solid #fecaca; }
  .del:hover { background: var(--danger); color: #fff; }
  .del-sm { background: transparent; color: var(--text-muted); border: 1px solid var(--border-color); font-size: 0.8rem; border-radius: 4px; cursor: pointer; padding: 4px 8px; }
  .del-sm:hover { color: var(--danger); border-color: var(--danger); }

  .empty-state { grid-column: 1 / -1; text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: 0.9rem; background: #f8fafc; border: 1px dashed var(--border-color); border-radius: var(--radius); }

  @media (max-width: 900px) {
    .main-layout { grid-template-columns: 1fr; }
    .card-form { position: relative; top: 0; }
    header { flex-direction: column; align-items: flex-start; }
    .header-right { width: 100%; justify-content: space-between; }
    .kpi-main { flex: 1; align-items: flex-start; box-sizing: border-box; }
  }
</style>
