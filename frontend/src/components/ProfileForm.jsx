import { useEffect, useState } from "react";
import {
  buildProfilePayload,
  createEmptyProfileValues,
  flattenProfileValues,
  profileFields
} from "../data/profileFields";

const defaultFormValues = createEmptyProfileValues();

export default function ProfileForm({ initialValues, onSubmit }) {
  const [formValues, setFormValues] = useState(defaultFormValues);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (initialValues) {
      setFormValues({
        ...defaultFormValues,
        ...flattenProfileValues(initialValues)
      });
      return;
    }

    setFormValues(defaultFormValues);
  }, [initialValues]);

  function handleChange(event) {
    const { name, value } = event.target;

    setFormValues((currentValues) => ({
      ...currentValues,
      [name]: value
    }));

    setErrors((currentErrors) => {
      if (!currentErrors[name]) {
        return currentErrors;
      }

      const nextErrors = { ...currentErrors };
      delete nextErrors[name];
      return nextErrors;
    });
  }

  function validateForm() {
    const nextErrors = {};

    profileFields.forEach((field) => {
      if (!formValues[field.name]) {
        nextErrors[field.name] = `${field.label} is required.`;
      }
    });

    return nextErrors;
  }

  function handleSubmit(event) {
    event.preventDefault();

    const nextErrors = validateForm();
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onSubmit(buildProfilePayload(formValues));
  }

  return (
    <form className="form-card card" onSubmit={handleSubmit} noValidate>
      <div className="form-grid">
        {profileFields.map((field) => (
          <SelectField
            key={field.name}
            name={field.name}
            label={field.label}
            hint={field.hint}
            value={formValues[field.name]}
            error={errors[field.name]}
            onChange={handleChange}
            options={field.options}
          />
        ))}
      </div>

      <div className="form-actions">
        <button className="button-primary" type="submit">
          Generate Mock Recommendation
        </button>
      </div>
    </form>
  );
}

function SelectField({ name, label, hint, value, error, onChange, options }) {
  return (
    <div className="field-group">
      <label htmlFor={name}>{label}</label>
      <select id={name} name={name} value={value} onChange={onChange}>
        <option value="">Select an option</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <p className="hint">{hint}</p>
      {error ? <p className="field-error">{error}</p> : null}
    </div>
  );
}
