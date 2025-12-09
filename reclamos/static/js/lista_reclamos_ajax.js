/**
 * Módulo AJAX para filtrado dinámico de lista de reclamos
 * Dependencias: jQuery 2.2.4, Bootstrap 3
 */

(function($) {
    'use strict';

    // Configuración
    const CONFIG = {
        apiUrl: '/api/lista-reclamos-ajax/',
        debounceDelay: 600,
        minCharsForTextSearch: 2
    };

    // Estado
    let debounceTimer = null;
    let currentRequest = null;
    let currentPage = 1;

    /**
     * Inicialización cuando el DOM está listo
     */
    $(document).ready(function() {
        init();
    });

    function init() {
        console.log('Inicializando filtros AJAX...');

        // Event listeners para filtros
        attachFilterListeners();

        // Event listener para paginación
        attachPaginationListeners();

        // Event listener para limpiar filtros
        $('#limpiar-filtros').on('click', limpiarFiltros);

        // Cargar filtros activos iniciales (si hay)
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.toString()) {
            renderFiltrosActivos(extractFiltrosActivosFromURL());
        }
    }

    /**
     * Adjunta listeners a todos los campos de filtro
     */
    function attachFilterListeners() {
        // Selectores (cambio inmediato)
        $('#id_estado, #id_tipo_de_reclamo').on('change', function() {
            console.log('Filtro selector cambiado:', this.id);
            currentPage = 1; // Reset a página 1
            performFilterWithDebounce(0); // Sin debounce para selectores
        });

        // Campos de fecha (cambio inmediato)
        $('#id_fecha_desde, #id_fecha_hasta').on('change', function() {
            console.log('Filtro fecha cambiado:', this.id);
            currentPage = 1;
            performFilterWithDebounce(0);
        });

        // Campo de búsqueda (con debounce)
        $('#id_busqueda').on('input', function() {
            console.log('Búsqueda cambiada');
            currentPage = 1;
            performFilterWithDebounce(CONFIG.debounceDelay);
        });
    }

    /**
     * Adjunta listeners a enlaces de paginación
     */
    function attachPaginationListeners() {
        $(document).on('click', '.pagination-link', function(e) {
            e.preventDefault();
            const page = $(this).data('page');
            console.log('Navegando a página:', page);
            currentPage = page;
            performFilter(false); // No resetear página
        });
    }

    /**
     * Ejecuta filtrado con debounce
     */
    function performFilterWithDebounce(delay) {
        clearTimeout(debounceTimer);

        if (delay === 0) {
            performFilter(true);
        } else {
            debounceTimer = setTimeout(function() {
                performFilter(true);
            }, delay);
        }
    }

    /**
     * Ejecuta el filtrado AJAX
     */
    function performFilter(resetPage) {
        if (resetPage) {
            currentPage = 1;
        }

        // Cancelar request anterior si existe
        if (currentRequest) {
            currentRequest.abort();
        }

        // Construir parámetros
        const params = collectFilterParams();
        params.page = currentPage;

        // Mostrar loading
        showLoading();

        // Request AJAX
        currentRequest = $.ajax({
            url: CONFIG.apiUrl,
            method: 'GET',
            data: params,
            dataType: 'json'
        })
        .done(function(response) {
            console.log('Respuesta recibida:', response);

            if (response.success) {
                // Actualizar tabla
                renderTabla(response.reclamos);

                // Actualizar paginación
                renderPaginacion(response.pagination);

                // Actualizar contador
                updateContador(response.pagination.total_items);

                // Actualizar badges de filtros activos
                renderFiltrosActivos(response.filtros_activos);

                // Actualizar URL sin recargar
                updateURL(params);
            } else {
                showError('Error al cargar resultados');
            }
        })
        .fail(function(xhr, status, error) {
            if (status !== 'abort') {
                console.error('Error AJAX:', error);
                showError('Error de conexión. Por favor, intente nuevamente.');
            }
        })
        .always(function() {
            hideLoading();
            currentRequest = null;
        });
    }

    /**
     * Recolecta parámetros de filtros del formulario
     */
    function collectFilterParams() {
        const params = {};

        // Tipo de vista
        params.vista_tipo = $('#vista-tipo').val();

        // Filtro de estado
        const estado = $('#id_estado').val();
        if (estado) params.estado = estado;

        // Filtro de tipo
        const tipo = $('#id_tipo_de_reclamo').val();
        if (tipo) params.tipo_de_reclamo = tipo;

        // Fechas
        const fechaDesde = $('#id_fecha_desde').val();
        if (fechaDesde) params.fecha_desde = fechaDesde;

        const fechaHasta = $('#id_fecha_hasta').val();
        if (fechaHasta) params.fecha_hasta = fechaHasta;

        // Búsqueda de texto
        const busqueda = $('#id_busqueda').val().trim();
        if (busqueda && busqueda.length >= CONFIG.minCharsForTextSearch) {
            params.busqueda = busqueda;
        }

        return params;
    }

    /**
     * Renderiza la tabla con nuevos datos
     */
    function renderTabla(reclamos) {
        const $tbody = $('#tabla-body');
        $tbody.empty();

        if (reclamos.length === 0) {
            $tbody.html('<tr><td colspan="14" style="text-align: center; padding: 20px;">No se encontraron resultados</td></tr>');
            return;
        }

        reclamos.forEach(function(rec) {
            const row = `
                <tr>
                    <td><div class="td_fecha">${rec.fecha}</div></td>
                    <td><div class="td_tipo">
                        <a href="/trabajos/${rec.n_de_reclamo}/">${rec.tipo_de_reclamo}</a>
                    </div></td>
                    <td><div class="td_apellido">${rec.apellido}</div></td>
                    <td><div class="td_calle">${rec.calle}</div></td>
                    <td><div class="td_altura">${rec.altura}</div></td>
                    <td><div class="td_telefono">${rec.telefono}</div></td>
                    <td><div class="td_detalle">${rec.detalle}</div></td>
                    <td><div class="td_estado">${rec.estado}</div></td>
                    <td><div class="td_partida">
                        ${rec.partida !== '-' ? '<a href="/partida/partida-' + rec.partida + '/">' + rec.partida + '</a>' : '-'}
                    </div></td>
                    <td><div class="td_fecha_resol">${rec.fecha_resolucion}</div></td>
                    <td><div class="td_tarea">${rec.tarea_realizada}</div></td>
                    <td><div class="td_operario">${rec.operarios}</div></td>
                    <td><div class="td_notificacion">${rec.notificacion}</div></td>
                    <td><div class="td_comentario">${rec.comentario}</div></td>
                </tr>
            `;
            $tbody.append(row);
        });

        // Re-aplicar sorttable si existe
        if (typeof sorttable !== 'undefined') {
            sorttable.makeSortable($('#tabla-reclamos')[0]);
        }
    }

    /**
     * Renderiza la paginación
     */
    function renderPaginacion(pagination) {
        let html = '<span class="step-links">';

        if (pagination.has_previous) {
            html += `<a href="#" class="pagination-link" data-page="1">« primera</a> `;
            html += `<a href="#" class="pagination-link" data-page="${pagination.previous_page}">anterior</a> `;
        }

        html += `<span class="current">| Página <span id="current-page">${pagination.current_page}</span> de <span id="total-pages">${pagination.total_pages}</span> |</span> `;

        if (pagination.has_next) {
            html += `<a href="#" class="pagination-link" data-page="${pagination.next_page}">siguiente</a> `;
            html += `<a href="#" class="pagination-link" data-page="${pagination.total_pages}">última »</a>`;
        }

        html += '</span>';

        $('#pagination-container').html(html);
    }

    /**
     * Actualiza contador de resultados
     */
    function updateContador(total) {
        $('#total-items').text(total);
    }

    /**
     * Renderiza badges de filtros activos
     */
    function renderFiltrosActivos(filtros) {
        const $container = $('#filtros-activos-container');
        $container.empty();

        const filtrosArray = Object.values(filtros);

        if (filtrosArray.length === 0) {
            return;
        }

        let html = '<div style="margin-bottom: 10px;"><strong>Filtros activos:</strong> ';

        filtrosArray.forEach(function(filtro) {
            html += `
                <span class="badge" style="margin-right: 5px; font-size: 11pt; padding: 5px 10px; background-color: #5bc0de;">
                    ${filtro.label}: ${filtro.value}
                    <a href="#" class="remove-filtro" data-param="${filtro.param}" style="color: white; margin-left: 5px;">
                        <span class="glyphicon glyphicon-remove"></span>
                    </a>
                </span>
            `;
        });

        html += '</div>';

        $container.html(html);

        // Event listener para remover filtros individuales
        $('.remove-filtro').on('click', function(e) {
            e.preventDefault();
            const param = $(this).data('param');
            removerFiltro(param);
        });
    }

    /**
     * Extrae filtros activos desde URL
     */
    function extractFiltrosActivosFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const filtros = {};

        const filterLabels = {
            'estado': 'Estado',
            'tipo_de_reclamo': 'Tipo',
            'fecha_desde': 'Desde',
            'fecha_hasta': 'Hasta',
            'busqueda': 'Búsqueda'
        };

        for (let [key, label] of Object.entries(filterLabels)) {
            const value = urlParams.get(key);
            if (value) {
                // Para selects, mostrar texto del option seleccionado
                let displayValue = value;
                const $select = $('#id_' + key);
                if ($select.is('select')) {
                    const selectedText = $select.find('option:selected').text();
                    if (selectedText && selectedText !== '----------' && selectedText !== 'Todos los estados' && selectedText !== 'Todos los tipos') {
                        displayValue = selectedText;
                    }
                }

                filtros[key] = {
                    label: label,
                    value: displayValue,
                    param: key
                };
            }
        }

        return filtros;
    }

    /**
     * Remueve un filtro específico
     */
    function removerFiltro(param) {
        // Limpiar el campo
        const $field = $('#id_' + param);
        if ($field.is('select')) {
            $field.val('');
        } else {
            $field.val('');
        }

        // Re-ejecutar filtrado
        currentPage = 1;
        performFilter(true);
    }

    /**
     * Limpia todos los filtros
     */
    function limpiarFiltros() {
        console.log('Limpiando todos los filtros...');

        // Limpiar explícitamente cada campo
        $('#id_estado').val('');
        $('#id_tipo_de_reclamo').val('');
        $('#id_fecha_desde').val('');
        $('#id_fecha_hasta').val('');
        $('#id_busqueda').val('');

        // Resetear página
        currentPage = 1;

        // Actualizar URL a la ruta base sin parámetros
        window.history.replaceState({}, '', window.location.pathname);

        // Ejecutar filtrado (esto cargará todos los registros sin filtros)
        performFilter(true);
    }

    /**
     * Actualiza la URL sin recargar la página
     */
    function updateURL(params) {
        const searchParams = new URLSearchParams();

        for (let [key, value] of Object.entries(params)) {
            if (key !== 'vista_tipo' && key !== 'page') { // No incluir vista_tipo ni page en URL
                searchParams.set(key, value);
            }
        }

        const newURL = window.location.pathname + (searchParams.toString() ? '?' + searchParams.toString() : '');

        // Usar history.replaceState para no agregar al historial
        window.history.replaceState({}, '', newURL);
    }

    /**
     * Muestra indicador de carga
     */
    function showLoading() {
        $('#loading-indicator').slideDown(200);
        $('#tabla-container').css('opacity', '0.5');
    }

    /**
     * Oculta indicador de carga
     */
    function hideLoading() {
        $('#loading-indicator').slideUp(200);
        $('#tabla-container').css('opacity', '1');
    }

    /**
     * Muestra mensaje de error
     */
    function showError(message) {
        const alertHtml = `
            <div class="alert alert-danger alert-dismissible" role="alert">
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
                <strong>Error:</strong> ${message}
            </div>
        `;

        $('#tabla-container').before(alertHtml);

        // Auto-cerrar después de 5 segundos
        setTimeout(function() {
            $('.alert-danger').fadeOut(300, function() {
                $(this).remove();
            });
        }, 5000);
    }

})(jQuery);
