/**
 * Módulo de búsqueda AJAX de partidas para nuevo_reclamo
 * Dependencias: jQuery (ya cargado en base.html)
 */

(function($) {
    'use strict';

    // Configuración
    const CONFIG = {
        minChars: 3,
        debounceDelay: 400,
        apiUrl: '/api/buscar-partidas/',
        messages: {
            minChars: 'Ingrese al menos 3 caracteres para buscar',
            searching: 'Buscando...',
            noResults: 'No se encontraron resultados',
            error: 'Error al realizar la búsqueda. Intente nuevamente.'
        }
    };

    // Estado
    let debounceTimer = null;
    let currentRequest = null;

    /**
     * Inicializa el buscador cuando el DOM está listo
     */
    function init() {
        const $searchInput = $('#buscar-partida');
        const $searchButton = $('#btn-buscar-partida');

        if ($searchInput.length === 0) {
            console.error('Input de búsqueda no encontrado');
            return;
        }

        // Event listeners
        $searchInput.on('input', handleSearchInput);
        $searchInput.on('keypress', function(e) {
            if (e.which === 13) { // Enter
                e.preventDefault();
                performSearch();
            }
        });

        if ($searchButton.length) {
            $searchButton.on('click', function(e) {
                e.preventDefault();
                performSearch();
            });
        }

        // Mostrar mensaje inicial
        showMessage('info', 'Ingrese dirección o nombre para buscar partidas');
    }

    /**
     * Maneja la entrada en el campo de búsqueda (con debounce)
     */
    function handleSearchInput() {
        clearTimeout(debounceTimer);

        const query = $('#buscar-partida').val().trim();

        if (query.length === 0) {
            clearResults();
            showMessage('info', 'Ingrese dirección o nombre para buscar partidas');
            return;
        }

        if (query.length < CONFIG.minChars) {
            clearResults();
            showMessage('warning', CONFIG.messages.minChars);
            return;
        }

        // Debounce: esperar 400ms después del último keystroke
        debounceTimer = setTimeout(performSearch, CONFIG.debounceDelay);
    }

    /**
     * Ejecuta la búsqueda AJAX
     */
    function performSearch() {
        const query = $('#buscar-partida').val().trim();

        if (query.length < CONFIG.minChars) {
            showMessage('warning', CONFIG.messages.minChars);
            return;
        }

        // Cancelar request anterior si existe
        if (currentRequest) {
            currentRequest.abort();
        }

        // Mostrar loading
        showLoading();

        // Realizar petición AJAX
        currentRequest = $.ajax({
            url: CONFIG.apiUrl,
            method: 'GET',
            data: { q: query },
            dataType: 'json',
            success: handleSearchSuccess,
            error: handleSearchError,
            complete: function() {
                currentRequest = null;
            }
        });
    }

    /**
     * Maneja respuesta exitosa de la búsqueda
     */
    function handleSearchSuccess(response) {
        hideLoading();

        if (!response.success) {
            showMessage('warning', response.message || CONFIG.messages.noResults);
            clearResults();
            return;
        }

        if (response.resultados.length === 0) {
            showMessage('info', CONFIG.messages.noResults);
            clearResults();
            return;
        }

        // Renderizar resultados
        renderResults(response.resultados);
        showMessage('success', response.message);
    }

    /**
     * Maneja errores de la búsqueda
     */
    function handleSearchError(xhr, status, error) {
        hideLoading();

        if (status === 'abort') {
            return; // Request cancelado, no mostrar error
        }

        console.error('Error en búsqueda:', error);
        showMessage('danger', CONFIG.messages.error);
        clearResults();
    }

    /**
     * Renderiza los resultados en una tabla HTML
     */
    function renderResults(resultados) {
        const $container = $('#resultados-partidas');

        if (resultados.length === 0) {
            $container.html('');
            return;
        }

        // Construir tabla HTML
        let html = '<table class="table table-striped table-hover table-condensed" id="tabla-partidas">';
        html += '<thead><tr>';
        html += '<th>Cuenta</th>';
        html += '<th>Partida</th>';
        html += '<th>Razón</th>';
        html += '<th>Calle</th>';
        html += '<th>N°</th>';
        html += '<th>Piso</th>';
        html += '<th>Dto.</th>';
        html += '</tr></thead>';
        html += '<tbody>';

        resultados.forEach(function(item) {
            const claseUnidad = item.tiene_trabajos ? 'unidad-con-trabajo' : 'unidad';
            const estiloUnidad = item.tiene_trabajos ? 'color:red' : '';

            html += '<tr class="fila-partida" style="cursor:pointer;">';
            html += `<td class="${claseUnidad}" style="font-weight:bold;${estiloUnidad}" data-unidad="${item.unidad}">${item.unidad}</td>`;
            html += `<td data-partida="${item.partida}"><a href="/partida/partida-${item.partida}" target="_blank">${item.partida}</a></td>`;
            html += `<td data-razon="${item.razon}">${item.razon}</td>`;
            html += `<td data-calle="${item.calle}">${item.calle}</td>`;
            html += `<td data-numero="${item.numero}">${item.numero}</td>`;
            html += `<td data-piso="${item.piso}">${item.piso}</td>`;
            html += `<td data-depto="${item.depto}">${item.depto}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table>';
        $container.html(html);

        // Agregar event listeners a las filas
        $('.fila-partida').on('click', handleRowClick);
    }

    /**
     * Maneja el click en una fila de resultados
     */
    function handleRowClick(e) {
        // No procesar si se hizo click en el link de partida
        if ($(e.target).is('a')) {
            return;
        }

        e.preventDefault();
        const $row = $(this);

        // Extraer datos de la fila usando data attributes
        const datos = {
            partida: $row.find('[data-partida]').data('partida'),
            razon: $row.find('[data-razon]').data('razon'),
            calle: $row.find('[data-calle]').data('calle'),
            numero: $row.find('[data-numero]').data('numero')
        };

        // Llenar formulario
        fillForm(datos);

        // Feedback visual
        $('.fila-partida').removeClass('info');
        $row.addClass('info');
    }

    /**
     * Llena el formulario de reclamo con los datos de la partida seleccionada
     */
    function fillForm(datos) {
        const $form = $('.nuevo_reclamo');

        // Mapear campos del formulario
        $form.find('input[name="partida"]').val(datos.partida || '');
        $form.find('input[name="apellido"]').val(capitalize(datos.razon || ''));
        $form.find('input[name="calle"]').val(capitalize(datos.calle || ''));
        $form.find('input[name="altura"]').val(datos.numero || '');

        // Scroll al formulario
        $('html, body').animate({
            scrollTop: $form.offset().top - 100
        }, 500);

        // Highlight temporal del campo partida
        const $partidaInput = $form.find('input[name="partida"]');
        $partidaInput.addClass('campo-actualizado');
        setTimeout(function() {
            $partidaInput.removeClass('campo-actualizado');
        }, 2000);
    }

    /**
     * Capitaliza texto (primera letra de cada palabra en mayúscula)
     */
    function capitalize(str) {
        if (!str) return '';
        return str.toLowerCase().replace(/\b\w/g, function(char) {
            return char.toUpperCase();
        });
    }

    /**
     * Muestra spinner de carga
     */
    function showLoading() {
        const $container = $('#resultados-partidas');
        const html = '<div class="text-center loading-spinner">' +
                    '<i class="glyphicon glyphicon-refresh glyphicon-spin"></i> ' +
                    CONFIG.messages.searching +
                    '</div>';
        $container.html(html);
    }

    /**
     * Oculta spinner de carga
     */
    function hideLoading() {
        $('.loading-spinner').remove();
    }

    /**
     * Muestra mensaje al usuario
     */
    function showMessage(type, text) {
        const $messageContainer = $('#mensaje-busqueda');
        const alertClass = 'alert alert-' + type;

        $messageContainer.html(`<div class="${alertClass}" style="margin-top:10px;">${text}</div>`);

        // Auto-hide para mensajes de éxito/info después de 5 segundos
        if (type === 'success' || type === 'info') {
            setTimeout(function() {
                $messageContainer.fadeOut(function() {
                    $(this).html('').show();
                });
            }, 5000);
        }
    }

    /**
     * Limpia los resultados
     */
    function clearResults() {
        $('#resultados-partidas').html('');
    }

    // Inicializar cuando el documento esté listo
    $(document).ready(init);

})(jQuery);
