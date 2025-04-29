document.addEventListener('DOMContentLoaded', function() {
    // Find the select element for the material field
    const selectField = document.querySelector('select[name="material"]');
    if (!selectField) {
        console.error("Material select field not found.");
        return;
    }

    // Hide the original select
    selectField.style.display = 'none';

    // Extract materials from the existing options
    const materials = Array.from(selectField.options).map(option => ({
        id: option.value,
        name: option.text
    }));

    // Create a new input for autocomplete
    const inputField = document.createElement('input');
    inputField.type = 'text';
    inputField.id = 'material_autocomplete';
    inputField.name = 'material_name'; // This isn't the real field name but used for UI
    inputField.placeholder = 'Buscar material...';
    inputField.style.marginTop = '5px'; // Optional, for better visual placement
    selectField.parentNode.insertBefore(inputField, selectField.nextSibling);

    // Create datalist for autocomplete
    const datalist = document.createElement('datalist');
    datalist.id = 'materials-list';
    inputField.setAttribute('list', 'materials-list');
    selectField.parentNode.insertBefore(datalist, inputField.nextSibling);

    inputField.addEventListener('input', function() {
        datalist.innerHTML = ''; // Clear previous options

        const searchTerm = this.value.toLowerCase();
        materials.forEach(material => {
            if (material.name.toLowerCase().includes(searchTerm)) {
                const option = document.createElement('option');
                option.value = material.name;
                datalist.appendChild(option);
            }
        });
    });

    // Handle selection to update the original select field
    inputField.addEventListener('change', function() {
        const selectedMaterial = materials.find(m => m.name === this.value);
        if (selectedMaterial) {
            // Update the hidden select with the correct value
            selectField.value = selectedMaterial.id;
        } else {
            // If no match, clear the select
            selectField.value = '';
        }
    });
});
