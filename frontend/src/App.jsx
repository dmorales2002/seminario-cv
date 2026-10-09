import {createContext, useContext, useEffect, useMemo, useState} from 'react'
import {Link, Navigate, Route, Routes, useNavigate, useParams} from 'react-router-dom'
import {api} from './api'

const AuthContext = createContext(null)
const useAuth = () => useContext(AuthContext)

function AuthProvider({children}) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(Boolean(localStorage.getItem('expediente_token')))
    useEffect(() => {
        if (!localStorage.getItem('expediente_token')) return
        api.me().then(setUser).catch(() => localStorage.removeItem('expediente_token')).finally(() => setLoading(false))
    }, [])
    const login = async (email, password) => {
        const token = await api.login(email, password)
        localStorage.setItem('expediente_token', token.access_token)
        const current = await api.me();
        setUser(current);
        return current
    }
    const logout = () => {
        localStorage.removeItem('expediente_token');
        setUser(null)
    }
    return <AuthContext.Provider value={{user, loading, login, logout}}>{children}</AuthContext.Provider>
}

function Protected({role, children}) {
    const {user, loading} = useAuth()
    if (loading) return <FullLoader label="Abriendo su expediente…"/>
    if (!user) return <Navigate to="/login" replace/>
    if (role && user.role !== role) return <Navigate to={user.role === 'RECRUITER' ? '/recruiter' : '/candidate'}
                                                     replace/>
    return children
}

function Shell({children, active}) {
    const {user, logout} = useAuth()
    const initials = user?.full_name?.split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase()
    const recruiter = user?.role === 'RECRUITER'
    return <>
        <header className="topbar">
            <Link className="brand" to={recruiter ? '/recruiter' : '/candidate'}>Expediente</Link>
            <nav aria-label="Navegación principal">
                <Link className={active === 'vacancies' ? 'active' : ''}
                      to={recruiter ? '/recruiter' : '/candidate'}>Vacantes</Link>
                {!recruiter && <Link className={active === 'applications' ? 'active' : ''} to="/candidate/applications">Mis
                    postulaciones</Link>}
            </nav>
            <div className="account"><span>{user?.full_name}</span>
                <button className="avatar" onClick={logout} title="Cerrar sesión">{initials}</button>
            </div>
        </header>
        <main className="page">{children}</main>
    </>
}

function FullLoader({label = 'Cargando…'}) {
    return <div className="full-loader"><span className="spinner"/>{label}</div>
}

function Alert({children, tone = 'error'}) {
    return children ? <div className={`alert ${tone}`}>{children}</div> : null
}

function Empty({title, text}) {
    return <div className="empty">
        <div className="empty-mark">◇</div>
        <h3>{title}</h3><p>{text}</p></div>
}

const formatDate = value => value ? new Intl.DateTimeFormat('es-GT', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
}).format(new Date(value)) : '—'
const statusLabel = {
    OPEN: 'Activa',
    PAUSED: 'Pausada',
    CLOSED: 'Cerrada',
    PENDING: 'Pendiente',
    APPROVED: 'Aprobado',
    REJECTED: 'Descartado'
}

function LoginPage({register = false}) {
    const {user, login} = useAuth();
    const navigate = useNavigate()
    const [form, setForm] = useState({full_name: '', email: '', password: '', role: 'CANDIDATE'})
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false)
    if (user) return <Navigate to={user.role === 'RECRUITER' ? '/recruiter' : '/candidate'} replace/>
    const submit = async e => {
        e.preventDefault();
        setBusy(true);
        setError('')
        try {
            if (register) await api.register(form)
            const current = await login(form.email, form.password)
            navigate(current.role === 'RECRUITER' ? '/recruiter' : '/candidate')
        } catch (err) {
            setError(err.message)
        } finally {
            setBusy(false)
        }
    }
    return <div className="auth-layout">
        <section className="auth-story"><span className="eyebrow">PRESELECCIÓN TRANSPARENTE</span><h1>Talento
            visible.<br/>Decisiones humanas.</h1><p>Expediente organiza candidatos por afinidad de habilidades y muestra
            la evidencia detrás de cada puntaje.</p>
            <div className="principles"></div>
        </section>
        <section className="auth-panel">
            <div className="auth-card">
                <div className="brand large">Expediente</div>
                <p className="muted">{register ? 'Cree una cuenta para comenzar.' : 'Ingrese para abrir su espacio de trabajo.'}</p>
                <Alert>{error}</Alert>
                <form onSubmit={submit}>
                    {register && <label>Nombre completo<input required value={form.full_name} onChange={e => setForm({
                        ...form,
                        full_name: e.target.value
                    })}/></label>}
                    <label>Correo electrónico<input type="email" required value={form.email}
                                                    onChange={e => setForm({...form, email: e.target.value})}/></label>
                    <label>Contraseña<input type="password" required minLength="8" value={form.password}
                                            onChange={e => setForm({...form, password: e.target.value})}/></label>
                    {register && <fieldset>
                        <legend>¿Cómo usará Expediente?</legend>
                        <div className="role-options"><label><input type="radio" name="role"
                                                                    checked={form.role === 'CANDIDATE'}
                                                                    onChange={() => setForm({
                                                                        ...form,
                                                                        role: 'CANDIDATE'
                                                                    })}/> Candidato</label><label><input type="radio"
                                                                                                         name="role"
                                                                                                         checked={form.role === 'RECRUITER'}
                                                                                                         onChange={() => setForm({
                                                                                                             ...form,
                                                                                                             role: 'RECRUITER'
                                                                                                         })}/> Reclutador</label>
                        </div>
                    </fieldset>}
                    <button className="button primary full"
                            disabled={busy}>{busy ? 'Procesando…' : register ? 'Crear cuenta' : 'Ingresar'}</button>
                </form>
                <p className="auth-switch">{register ? '¿Ya tiene una cuenta?' : '¿Aún no tiene cuenta?'} <Link
                    to={register ? '/login' : '/register'}>{register ? 'Ingresar' : 'Registrarse'}</Link></p></div>
        </section>
    </div>
}

function RecruiterDashboard() {
    const [vacancies, setVacancies] = useState([]);
    const [loading, setLoading] = useState(true)
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState('')
    const load = () => api.myVacancies().then(setVacancies).catch(e => setError(e.message)).finally(() => setLoading(false))
    useEffect(() => {
        load()
    }, [])
    const totals = useMemo(() => ({
        pending: vacancies.reduce((n, v) => n + v.pending_count, 0),
        applications: vacancies.reduce((n, v) => n + v.application_count, 0),
        active: vacancies.filter(v => v.status === 'OPEN').length,
    }), [vacancies])
    return <Shell active="vacancies">
        <div className="heading-row">
            <div><span className="eyebrow">PANEL DEL RECLUTADOR</span><h1>Mis vacantes</h1>
                <p>{totals.pending} candidatos esperan revisión</p></div>
            <button className="button primary" onClick={() => setCreating(true)}>＋ Publicar vacante</button>
        </div>
        <Alert>{error}</Alert>
        <div className="stats"><Stat label="Por revisar" value={totals.pending} accent/><Stat
            label="Postulaciones totales" value={totals.applications}/><Stat label="Vacantes activas"
                                                                             value={totals.active}/></div>
        {loading ? <FullLoader/> : vacancies.length === 0 ? <Empty title="Aún no hay vacantes"
                                                                   text="Publique la primera vacante para comenzar a recibir postulaciones."/> :
            <div className="table-card">
                <table>
                    <thead>
                    <tr>
                        <th>Vacante</th>
                        <th>Estado</th>
                        <th>Postulaciones</th>
                        <th>Por revisar</th>
                        <th>Publicada</th>
                        <th/>
                    </tr>
                    </thead>
                    <tbody>{vacancies.map(v => <tr key={v.id}>
                        <td><strong>{v.title}</strong><small>VAC-{v.id.slice(0, 6).toUpperCase()}</small></td>
                        <td><Badge status={v.status}/></td>
                        <td>{v.application_count}</td>
                        <td className="accent-number">{v.pending_count}</td>
                        <td>{formatDate(v.created_at)}</td>
                        <td><Link className="text-link" to={`/recruiter/vacancies/${v.id}`}>Abrir expediente →</Link>
                        </td>
                    </tr>)}</tbody>
                </table>
            </div>}
        {creating && <VacancyModal onClose={() => setCreating(false)} onCreated={() => {
            setCreating(false);
            load()
        }}/>}
    </Shell>
}

function Stat({label, value, accent}) {
    return <div className="stat"><span>{label}</span><strong className={accent ? 'terracotta' : ''}>{value}</strong>
    </div>
}

function Badge({status}) {
    return <span className={`badge ${status.toLowerCase()}`}>{statusLabel[status] || status}</span>
}

function VacancyModal({onClose, onCreated}) {
    const [form, setForm] = useState({title: '', description: '', requirements: ''});
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('')
    const submit = async e => {
        e.preventDefault();
        setBusy(true);
        try {
            await api.createVacancy(form);
            onCreated()
        } catch (err) {
            setError(err.message);
            setBusy(false)
        }
    }
    return <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}>
        <section className="modal wide">
            <button className="modal-close" onClick={onClose}>×</button>
            <span className="eyebrow">NUEVA VACANTE</span><h2>Publicar una vacante</h2><p className="muted">Describa las
            actividades con claridad; el motor extraerá los criterios después de publicarla.</p><Alert>{error}</Alert>
            <form onSubmit={submit}><label>Título del puesto<input required value={form.title} onChange={e => setForm({
                ...form,
                title: e.target.value
            })}/></label><label>Descripción general<textarea required rows="4" value={form.description}
                                                             onChange={e => setForm({
                                                                 ...form,
                                                                 description: e.target.value
                                                             })}/></label><label>Requisitos y actividades<textarea
                required rows="6" value={form.requirements}
                onChange={e => setForm({...form, requirements: e.target.value})}/></label>
                <div className="info-strip">ⓘ No solicite edad, años de experiencia ni grado académico: no forman parte
                    del cálculo.
                </div>
                <div className="modal-actions">
                    <button type="button" className="button ghost" onClick={onClose}>Cancelar</button>
                    <button className="button primary"
                            disabled={busy}>{busy ? 'Publicando…' : 'Publicar vacante'}</button>
                </div>
            </form>
        </section>
    </div>
}

function VacancyWorkspace() {
    const {id} = useParams();
    const navigate = useNavigate()
    const [vacancy, setVacancy] = useState(null);
    const [apps, setApps] = useState([]);
    const [criteria, setCriteria] = useState(null)
    const [selected, setSelected] = useState(null);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState('');
    const [tab, setTab] = useState('ranking')
    const load = async () => {
        try {
            const [mine, ranking] = await Promise.all([api.myVacancies(), api.applications(id)]);
            setVacancy(mine.find(v => v.id === id));
            setApps(ranking);
            setSelected(s => ranking.find(x => x.id === s?.id) || ranking[0] || null);
            try {
                setCriteria(await api.getCriteria(id))
            } catch {
                setCriteria(null)
            }
        } catch (e) {
            setError(e.message)
        }
    }
    useEffect(() => {
        load()
    }, [id])
    const analyze = async () => {
        setBusy('analysis');
        setError('');
        try {
            await api.runAnalysis(id);
            await load()
        } catch (e) {
            setError(e.message)
        } finally {
            setBusy('')
        }
    }
    const extract = async () => {
        setBusy('criteria');
        try {
            setCriteria(await api.extractCriteria(id));
            await load()
        } catch (e) {
            setError(e.message)
        } finally {
            setBusy('')
        }
    }
    const decide = async status => {
        if (status === 'REJECTED' && !window.confirm('¿Confirma que desea descartar a este candidato?')) return;
        setBusy('decision');
        try {
            await api.decide(id, selected.id, status);
            await load()
        } catch (e) {
            setError(e.message)
        } finally {
            setBusy('')
        }
    }
    if (!vacancy && !error) return <Shell><FullLoader/></Shell>
    return <Shell active="vacancies">
        <button className="back-link" onClick={() => navigate('/recruiter')}>← Volver a mis vacantes</button>
        <div className="workspace-head">
            <div><span className="eyebrow">VAC-{id.slice(0, 6).toUpperCase()}</span><h1>{vacancy?.title}</h1>
                <div className="inline-meta"><Badge
                    status={vacancy?.status || 'OPEN'}/><span>{apps.length} postulaciones</span></div>
            </div>
            <div className="head-actions">
                <button className="button ghost" onClick={extract}
                        disabled={busy}>{criteria ? 'Reextraer criterios' : 'Extraer criterios'}</button>
                <button className="button primary" onClick={analyze}
                        disabled={busy || apps.length === 0}>{busy === 'analysis' ? 'Analizando…' : 'Analizar candidatos'}</button>
            </div>
        </div>
        <Alert>{error}</Alert>
        <div className="tabs">
            <button className={tab === 'ranking' ? 'active' : ''} onClick={() => setTab('ranking')}>Ranking y
                evidencia
            </button>
            <button className={tab === 'criteria' ? 'active' : ''} onClick={() => setTab('criteria')}>Criterios
                ({criteria?.criteria?.length || 0})
            </button>
        </div>
        {tab === 'criteria' ? <CriteriaEditor data={criteria} vacancyId={id} onSaved={load}/> :
            <div className="ranking-layout"><CandidateTable applications={apps} selected={selected}
                                                            onSelect={setSelected}/><CandidateDetail
                application={selected} vacancyId={id} busy={busy} onDecide={decide}/></div>}
    </Shell>
}

function CandidateTable({applications, selected, onSelect}) {
    if (!applications.length) return <Empty title="No hay postulaciones"
                                            text="Cuando se postule un candidato aparecerá aquí; el sistema nunca descarta automáticamente."/>
    return <div className="candidate-list">
        <div className="list-note">Ordenados por afinidad · Los puntajes orientan, no deciden</div>
        {applications.map((a, i) => <button key={a.id}
                                            className={`candidate-row ${selected?.id === a.id ? 'selected' : ''}`}
                                            onClick={() => onSelect(a)}><span className="rank">{i + 1}</span><span
            className="candidate-main"><strong>{a.candidate_name}</strong><small>{a.candidate_email}</small><Badge
            status={a.status}/></span><span className="score">{a.ai_score == null ? '—' : a.ai_score}<small>/100</small></span>
        </button>)}</div>
}

function CandidateDetail({application, vacancyId, busy, onDecide}) {
    const [resumeError, setResumeError] = useState('')
    if (!application) return <section className="detail-panel"><Empty title="Seleccione un candidato"
                                                                      text="Abra un expediente para revisar el puntaje y sus evidencias."/>
    </section>
    const factors = application.ai_evidence?.factors || [];
    const covered = factors.filter(f => f.match_strength === 1).length;
    const partial = factors.filter(f => f.match_strength === .5).length
    const openResume = async () => {
        setResumeError('');
        try {
            await api.openResume(vacancyId, application.id)
        } catch (e) {
            setResumeError(e.message)
        }
    }
    return <section className="detail-panel">
        <div className="candidate-title">
            <div
                className="avatar large">{application.candidate_name?.split(/\s+/).slice(0, 2).map(x => x[0]).join('')}</div>
            <div><span className="eyebrow">EXPEDIENTE DEL CANDIDATO</span><h2>{application.candidate_name}</h2>
                <button className="text-link button-link" onClick={openResume}>▣ Ver currículum original</button>
            </div>
            <div className="big-score">
                <span>Afinidad</span><strong>{application.ai_score ?? '—'}</strong><small>{application.ai_score != null ? '/ 100' : 'Sin analizar'}</small>
            </div>
        </div>
        <Alert>{resumeError}</Alert>
        {application.analysis_status === 'FAILED' && <Alert>{application.analysis_error}</Alert>}
        {!factors.length ?
            <div className="analysis-placeholder"><h3>Este expediente aún no tiene análisis</h3><p>Ejecute el motor para
                comparar habilidades y actividades con la vacante.</p></div> : <>
                <div className="evidence-summary">
                    <span><strong>{covered}</strong> cubiertos</span><span><strong>{partial}</strong> parciales</span><span><strong>{factors.length - covered - partial}</strong> sin evidencia</span><span>Calculado {formatDate(application.analyzed_at)}</span>
                </div>
                <div className="evidence-list">{factors.map((f, i) => <EvidenceCard key={`${f.criterion}-${i}`}
                                                                                    factor={f}/>)}</div>
            </>}
        <div className="decision-bar">
            <div><span className="eyebrow">DECISIÓN HUMANA</span><p>El sistema propone un orden; usted decide quién
                avanza.</p></div>
            <button className="button danger-ghost" disabled={busy} onClick={() => onDecide('REJECTED')}>Descartar
            </button>
            <button className="button primary" disabled={busy} onClick={() => onDecide('APPROVED')}>Aprobar para
                siguiente etapa
            </button>
        </div>
    </section>
}

export function EvidenceCard({factor}) {
    const state = factor.match_strength === 1 ? 'covered' : factor.match_strength === .5 ? 'partial' : 'missing'
    return <article className={`evidence ${state}`}>
        <header><span
            className="evidence-icon">{state === 'covered' ? '✓' : state === 'partial' ? '◐' : '×'}</span><strong>{factor.criterion}</strong><span
            className="kind">{factor.kind === 'SKILL' ? 'Habilidad' : 'Actividad'}</span><span
            className="weight">Peso {(factor.weight / 100).toFixed(2)} · +{factor.contribution}</span><Badge
            status={state === 'covered' ? 'CUBIERTO' : state === 'partial' ? 'PARCIAL' : 'SIN_EVIDENCIA'}/></header>
        {factor.evidence_quote ?
            <div className="evidence-body"><small>Fragmento del currículum · {factor.evidence_section}</small>
                <blockquote>«{factor.evidence_quote}»</blockquote>
                <p>{factor.rationale}</p></div> :
            <div className="evidence-body muted">No se encontró evidencia verificable en el currículum.</div>}</article>
}

function CriteriaEditor({data, vacancyId, onSaved}) {
    const [items, setItems] = useState(data?.criteria || []);
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState('')
    useEffect(() => setItems(data?.criteria || []), [data])
    if (!data) return <Empty title="Aún no hay criterios"
                             text="Use “Extraer criterios” para identificar habilidades y actividades en la vacante."/>
    const update = (i, key, value) => setItems(items.map((x, n) => n === i ? {
        ...x,
        [key]: key === 'weight' ? Number(value) : value
    } : x))
    const save = async () => {
        setBusy(true);
        setMessage('');
        try {
            await api.updateCriteria(vacancyId, items);
            setMessage('Criterios guardados. Los puntajes anteriores fueron invalidados.');
            onSaved()
        } catch (e) {
            setMessage(e.message)
        } finally {
            setBusy(false)
        }
    }
    return <section className="criteria-panel">
        <div className="criteria-intro">
            <div><h2>Criterios de afinidad</h2><p>Revise lo detectado por el motor. La API normalizará los pesos para
                sumar 100.</p></div>
            <span className="badge human">Fuente: {data.source === 'HUMAN' ? 'Revisión humana' : 'LLM'}</span></div>
        <Alert tone="success">{message}</Alert>
        <div className="criteria-grid">{items.map((item, i) => <div className="criterion-card" key={i}>
            <label>Nombre<input value={item.name} onChange={e => update(i, 'name', e.target.value)}/></label><label>Tipo<select
            value={item.kind} onChange={e => update(i, 'kind', e.target.value)}>
            <option value="SKILL">Habilidad</option>
            <option value="ACTIVITY">Actividad</option>
        </select></label><label>Peso<input type="number" min="0.1" max="100" step="0.1" value={item.weight}
                                           onChange={e => update(i, 'weight', e.target.value)}/></label><label
            className="criterion-description">Descripción<input value={item.description}
                                                                onChange={e => update(i, 'description', e.target.value)}/></label>
            <button className="icon-button" onClick={() => setItems(items.filter((_, n) => n !== i))}
                    aria-label={`Eliminar ${item.name}`}>×
            </button>
        </div>)}</div>
        <button className="button ghost" onClick={() => setItems([...items, {
            name: 'Nuevo criterio',
            kind: 'SKILL',
            description: '',
            weight: 1
        }])}>＋ Agregar criterio
        </button>
        <div className="criteria-footer">
            <div className="info-strip">ⓘ No se consideran antigüedad ni grado académico.</div>
            <button className="button primary" disabled={busy || !items.length}
                    onClick={save}>{busy ? 'Guardando…' : 'Guardar criterios'}</button>
        </div>
    </section>
}

function CandidateVacancies({applicationsOnly = false}) {
    const [vacancies, setVacancies] = useState([]);
    const [applications, setApplications] = useState([]);
    const [selected, setSelected] = useState(null);
    const [file, setFile] = useState(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('')
    const [downloadingId, setDownloadingId] = useState(null)
    const load = async () => {
        try {
            const [v, a] = await Promise.all([api.vacancies(), api.myApplications()]);
            setVacancies(v);
            setApplications(a);
            setSelected(s => v.find(x => x.id === s?.id) || v[0] || null)
        } catch (e) {
            setError(e.message)
        }
    }
    useEffect(() => {
        load()
    }, [])
    const applied = id => applications.find(a => a.vacancy_id === id)
    const apply = async () => {
        if (!file) {
            setError('Seleccione su CV en PDF o DOCX.');
            return
        }
        setBusy(true);
        setError('');
        try {
            await api.apply(selected.id, file);
            setFile(null);
            await load()
        } catch (e) {
            setError(e.message)
        } finally {
            setBusy(false)
        }
    }
    const downloadHarvard = async (vacancyId, applicationId) => {
        setDownloadingId(applicationId)
        setError('')
        try {
            await api.downloadHarvardResume(vacancyId, applicationId)
        } catch (e) {
            setError(e.message)
        } finally {
            setDownloadingId(null)
        }
    }
    if (applicationsOnly) return <Shell active="applications">
        <div className="heading-row">
            <div><span className="eyebrow">SEGUIMIENTO</span><h1>Mis postulaciones</h1><p>El estado siempre refleja una
                decisión de una persona.</p></div>
        </div>
        <Alert>{error}</Alert>{applications.length ? <div className="table-card">
        <table>
            <thead>
            <tr>
                <th>Vacante</th>
                <th>Fecha</th>
                <th>Estado</th>
                <th>CV Harvard</th>
            </tr>
            </thead>
            <tbody>{applications.map(a => {
                const v = vacancies.find(x => x.id === a.vacancy_id);
                return <tr key={a.id}>
                    <td><strong>{v?.title || 'Vacante'}</strong></td>
                    <td>{formatDate(a.applied_at)}</td>
                    <td><Badge status={a.status}/></td>
                    <td><button
                        className="button small"
                        disabled={downloadingId === a.id}
                        onClick={() => downloadHarvard(a.vacancy_id, a.id)}
                    >{downloadingId === a.id ? 'Generando…' : 'Descargar PDF'}</button></td>
                </tr>
            })}</tbody>
        </table>
    </div> : <Empty title="No tiene postulaciones" text="Explore las vacantes activas y postúlese con su currículum."/>}
    </Shell>
    return <Shell active="vacancies">
        <div className="heading-row">
            <div><span className="eyebrow">OPORTUNIDADES</span><h1>Vacantes activas</h1><p>{vacancies.length} plazas
                disponibles en la plataforma</p></div>
        </div>
        <Alert>{error}</Alert>
        <div className="jobs-layout">
            <div className="jobs-list">{vacancies.map(v => <button key={v.id}
                                                                   className={`job-card ${selected?.id === v.id ? 'selected' : ''}`}
                                                                   onClick={() => setSelected(v)}>
                <div><h2>{v.title}</h2><p>{v.description}</p></div>
                <span className="code">VAC-{v.id.slice(0, 6).toUpperCase()}</span>
                <div className="job-footer">
                    <span>Publicada {formatDate(v.created_at)}</span><strong>{applied(v.id) ? `Postulación ${statusLabel[applied(v.id).status].toLowerCase()}` : 'Ver detalle →'}</strong>
                </div>
            </button>)}</div>
            {selected && <aside className="job-detail"><span className="eyebrow">DETALLE DE LA VACANTE</span>
                <h2>{selected.title}</h2><h3>Descripción</h3><p>{selected.description}</p><h3>Requisitos y
                    actividades</h3><p className="preline">{selected.requirements}</p>{applied(selected.id) ?
                    <div className="success-box">✓ Ya se postuló a esta
                        vacante.<br/><small>Estado: {statusLabel[applied(selected.id).status]}</small></div> : <><label
                        className="file-drop">Currículum PDF o DOCX<input type="file" accept=".pdf,.docx"
                                                                          onChange={e => setFile(e.target.files[0])}/><span>{file?.name || 'Seleccione un archivo (máx. 5 MB)'}</span></label>
                        <button className="button primary full" disabled={busy}
                                onClick={apply}>{busy ? 'Enviando…' : 'Postularme a esta vacante'}</button>
                        <p className="human-note">Su postulación será revisada por una persona.<br/>El sistema ordena
                            candidatos, no toma la decisión.</p></>}</aside>}</div>
    </Shell>
}

export default function App() {
    return <AuthProvider><Routes>
        <Route path="/login" element={<LoginPage/>}/><Route path="/register" element={<LoginPage register/>}/>
        <Route path="/recruiter" element={<Protected role="RECRUITER"><RecruiterDashboard/></Protected>}/>
        <Route path="/recruiter/vacancies/:id" element={<Protected role="RECRUITER"><VacancyWorkspace/></Protected>}/>
        <Route path="/candidate" element={<Protected role="CANDIDATE"><CandidateVacancies/></Protected>}/>
        <Route path="/candidate/applications"
               element={<Protected role="CANDIDATE"><CandidateVacancies applicationsOnly/></Protected>}/>
        <Route path="*" element={<Navigate to="/login" replace/>}/>
    </Routes></AuthProvider>
}
