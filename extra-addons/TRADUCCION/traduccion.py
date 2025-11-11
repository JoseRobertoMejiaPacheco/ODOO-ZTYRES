# === Uso (odoo shell) ===
# $ odoo shell -d TU_DB
# >>> xml = qweb_export_fusionado(env, "account.report_invoice_with_payments",
# ...                             new_t_name="custom.report_invoice_with_payments_es_mx")
# >>> from pathlib import Path; Path("/tmp/report_invoice_with_payments_fusionado.xml").write_text(xml, encoding="utf-8")
#
# Ese archivo puedes pegarlo a un módulo como:
# <odoo>
#   <data>
#     <template id="report_invoice_with_payments_es_mx" name="Invoice with payments ES/MX" inherit_id="False">
#       ... (contenido que te genera este script) ...
#     </template>
#   </data>
# </odoo>
#
# Y luego crear un ir.actions.report apuntando a new_t_name.

from lxml import etree
from copy import deepcopy

QWEB_NS = None  # QWeb va sin namespace; mantenerlo así

# -------- Utilidades DOM --------
def _xpath(node, expr):
    return node.xpath(expr)

def _deepcopy(node):
    return deepcopy(node)

def _as_root(fragment_children):
    root = etree.Element("t")  # contenedor neutro
    for ch in fragment_children:
        root.append(_deepcopy(ch))
    return root

def _strip_branding(node):
    # Limpia atributos de branding de Odoo (data-oe-*)
    for el in node.xpath('.//*[@*]'):
        for a in list(el.attrib):
            if a.startswith('data-oe-'):
                del el.attrib[a]

def _pretty_xml(elem):
    return etree.tostring(elem, encoding="utf-8", xml_declaration=False, pretty_print=True).decode("utf-8")

# -------- Carga de templates desde ir.ui.view --------
def _load_qweb_templates(env):
    # Trae TODAS las vistas qweb: key (t-name), arch_db (XML string)
    views = env["ir.ui.view"].sudo().search([("type", "=", "qweb")])
    by_key = {}
    for v in views:
        # "key" es module.xml_id => mejor usar t-name principal si existe
        k = v.key or ""
        try:
            arch = etree.fromstring(v.arch_db.encode("utf-8"))
        except Exception:
            continue
        # detectar <template t-name="...">
        tname = arch.get("t-name") or arch.get("name")
        if tname:
            by_key[tname] = arch
        # también registrar por xmlid si aporta
        if k and k not in by_key:
            by_key[k] = arch
    return by_key

# -------- Motor simplificado de fusión QWeb --------
def _resolve_t_call(root, templates):
    """Expande <t t-call="name"> reemplazándolo por el cuerpo del template llamado, recursivo."""
    calls = root.xpath('.//t[@t-call]')
    for call in calls:
        name = call.get("t-call")
        tpl = templates.get(name)
        if tpl is None:
            # insertar comentario para resolver a mano
            comment = etree.Comment(f" FALTA t-call='{name}' (no encontrado) ")
            call.addprevious(comment)
            call.getparent().remove(call)
            continue
        # cuerpo del template llamado = hijos del <template ...> principal
        called_body = [ch for ch in tpl if isinstance(ch.tag, str)]
        injected = [ _deepcopy(ch) for ch in called_body ]
        # Resolver t-call recursivamente dentro del inyectado
        for inj in injected:
            _resolve_t_call(inj, templates)
        # Reemplazo: contenido del <t t-call> se ignora (se asume vacío)
        parent = call.getparent()
        idx = parent.index(call)
        parent.remove(call)
        for i, el in enumerate(injected):
            parent.insert(idx + i, el)

def _apply_t_jquery_op(base_dom, op_node):
    """Aplica una operación t-jquery al DOM base (replace/append/prepend/before/after/inner)."""
    jq = op_node.get("t-jquery")
    op = op_node.get("t-operation", "replace")
    if not jq:
        return
    targets = base_dom.xpath(jq)
    if not targets:
        # Comentario para que el usuario lo vea
        base_dom.append(etree.Comment(f" t-jquery='{jq}' sin coincidencias "))
        return

    payload_children = [ _deepcopy(ch) for ch in op_node if isinstance(ch.tag, str) ]
    if op == "replace":
        for t in targets:
            parent = t.getparent()
            if parent is None: continue
            idx = parent.index(t)
            parent.remove(t)
            for i, el in enumerate(payload_children):
                parent.insert(idx + i, _deepcopy(el))
    elif op == "inner":
        for t in targets:
            for c in list(t):
                t.remove(c)
            for el in payload_children:
                t.append(_deepcopy(el))
    elif op == "append":
        for t in targets:
            for el in payload_children:
                t.append(_deepcopy(el))
    elif op == "prepend":
        for t in targets:
            for i, el in enumerate(payload_children):
                t.insert(i, _deepcopy(el))
    elif op == "before":
        for t in targets:
            p = t.getparent()
            if p is None: continue
            idx = p.index(t)
            for i, el in enumerate(payload_children):
                p.insert(idx + i, _deepcopy(el))
    elif op == "after":
        for t in targets:
            p = t.getparent()
            if p is None: continue
            idx = p.index(t)
            for i, el in enumerate(payload_children):
                p.insert(idx + 1 + i, _deepcopy(el))
    else:
        base_dom.append(etree.Comment(f" t-operation='{op}' no soportada; aplicar manualmente "))

def _resolve_t_extend(root, templates):
    """
    Resuelve <t t-extend="..."> aplicando sus hijos <xpath...> o <t t-jquery...>.
    Retorna un DOM con la extensión aplicada.
    """
    extends = root.xpath('.//t[@t-extend]')
    for ext in extends:
        name = ext.get("t-extend")
        base_tpl = templates.get(name)
        if base_tpl is None:
            ext.addprevious(etree.Comment(f" FALTA t-extend='{name}' (no encontrado) "))
            ext.getparent().remove(ext)
            continue

        # 1) Clonar el base
        base_dom = _as_root([ch for ch in base_tpl if isinstance(ch.tag, str)])

        # 2) Aplicar operaciones <t t-jquery...> (o <xpath> legacy si existiera)
        #    Soportamos las comunes: replace, inner, append, prepend, before, after
        for op in ext:
            if isinstance(op.tag, str) and op.tag == "t" and (op.get("t-jquery") or op.get("t-operation")):
                _apply_t_jquery_op(base_dom, op)
            elif isinstance(op.tag, str) and op.tag == "xpath":
                # Compat: xpath expr + position
                expr = op.get("expr")
                pos = op.get("position", "replace")
                targets = base_dom.xpath(expr) if expr else []
                payload = [ _deepcopy(ch) for ch in op if isinstance(ch.tag, str) ]
                if not targets:
                    base_dom.append(etree.Comment(f" xpath expr='{expr}' sin coincidencias "))
                else:
                    for t in targets:
                        p = t.getparent()
                        if pos == "replace":
                            idx = p.index(t); p.remove(t)
                            for i, el in enumerate(payload): p.insert(idx+i, _deepcopy(el))
                        elif pos == "inside":
                            for el in payload: t.append(_deepcopy(el))
                        elif pos == "before":
                            idx = p.index(t)
                            for i, el in enumerate(payload): p.insert(idx+i, _deepcopy(el))
                        elif pos == "after":
                            idx = p.index(t)
                            for i, el in enumerate(payload): p.insert(idx+1+i, _deepcopy(el))
                        else:
                            base_dom.append(etree.Comment(f" xpath position='{pos}' no soportada "))

        # 3) Reemplazar el nodo <t t-extend> por el base_dom ya modificado
        parent = ext.getparent()
        idx = parent.index(ext)
        parent.remove(ext)
        for i, ch in enumerate(list(base_dom)):
            parent.insert(idx + i, _deepcopy(ch))

    # Como pudo haber nuevos t-extend dentro, repetir hasta estabilizar
    again = root.xpath('.//t[@t-extend]')
    if again:
        _resolve_t_extend(root, templates)

def _fuse_qweb_template(templates, entry_name):
    if entry_name not in templates:
        raise ValueError(f"No encontré el template '{entry_name}' en ir.ui.view.")
    # Partimos del template principal
    entry = _deepcopy(templates[entry_name])
    # 1) Resolver t-extend (aplica parches sobre bases)
    _resolve_t_extend(entry, templates)
    # 2) Resolver t-call (expandir inclusiones)
    _resolve_t_call(entry, templates)
    # Limpia branding
    _strip_branding(entry)
    return entry

# -------- API principal --------
def qweb_export_fusionado(env, entry_t_name: str, *, new_t_name: str = None, new_template_id: str = None) -> str:
    """
    Devuelve **QWeb XML fusionado** (no HTML) del template `entry_t_name` con
    t-extend/t-call resueltos (operaciones comunes).
    - new_t_name: si lo das, se pondrá como t-name en el resultado (recomendado).
    - new_template_id: si lo das, se pondrá 'id' para pegarlo directo en un data.xml.

    Copia y pega el resultado en tu módulo y crea un ir.actions.report que apunte a new_t_name.
    """
    templates = _load_qweb_templates(env)
    fused = _fuse_qweb_template(templates, entry_t_name)

    # Empaquetar en <template>
    out_tpl = etree.Element("template")
    if new_template_id:
        out_tpl.set("id", new_template_id)
    out_tpl.set("name", (new_t_name or f"{entry_t_name}_fused").split(".")[-1])
    out_tpl.set("inherit_id", "False")
    if new_t_name:
        out_tpl.set("t-name", new_t_name)
    else:
        out_tpl.set("t-name", f"{entry_t_name}_fused")

    # Mover el cuerpo fusionado dentro del template de salida
    for ch in fused:
        out_tpl.append(_deepcopy(ch))

    # Resultado final serializado
    xml = _pretty_xml(out_tpl)
    # Envuélvelo como bloque listo para módulo si quieres:
    # <odoo><data noupdate="1"> ...xml... </data></odoo>
    return xml

# === Ejemplo para tu caso ===
xml = qweb_export_fusionado(env,
        "account.report_invoice_with_payments",
        new_t_name="custom.report_invoice_with_payments_ennnn",
        new_template_id="report_invoice_with_payments_ennnn")
# from pathlib import Path; Path("/tmp/report_invoice_with_payments_fusionado.xml").write_text(xml, encoding="utf-8")
