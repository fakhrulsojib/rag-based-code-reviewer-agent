# Entity Code Review Checklist

## 1. Core Entity Structure

- [ ] **Implementation**: Is the entity a POJO? Does it inherit from `Persistent` or implement `Serializable` if standalone?
- [ ] **Primary Key**:
    - [ ] Is the primary key an `int` or `long` named `id`?
    - [ ] Is it annotated with `@Id`?
    - [ ] Is the value generated using a sequence with `@GeneratedValue` and `@SequenceGenerator`?
- [ ] **`serialVersionUID`**: Is a `private static final long serialVersionUID` declared?

## 2. Annotations and Naming

- [ ] **`@Entity`**: Does the class have the `@Entity` annotation?
- [ ] **`@Table`**: Is the table name defined in snake_case using `@Table(name = "...")`?
- [ ] **`@NamedQueries`**: Are complex or frequently used queries defined using `@NamedQueries`?
- [ ] **Column Naming**: Are column names specified with `@Column(name = "...")` if they differ from the field name or use snake_case?
- [ ] **Validation**:
    - [ ] Are Java Bean Validation annotations (`@NotNull`, `@Size`, etc.) used for data integrity?
    - [ ] Is `@NotEmpty` used for non-empty `String` fields?
- [ ] **Enums**: Is `@Enumerated(EnumType.STRING)` used for enum fields?

## 3. Relationships (`@ManyToOne`, `@OneToMany`)

- [ ] **`@ManyToOne`**:
    - [ ] Is `@Fetch(value = SELECT)` used to prevent n+1 problems?
    - [ ] Is `@JoinColumn` with `optional = false` used for mandatory relationships?
- [ ] **`@OneToMany`**:
    - [ ] Are `cascade = CascadeType.ALL` and `orphanRemoval = true` used for managing child entities?
    - [ ] Is `@JoinColumn` used on the parent side for unidirectional relationships?
    - [ ] Is `@OrderColumn(name = "idx")` used to maintain list order?

## 4. Special-Purpose Patterns

- [ ] **Archiving**:
    - [ ] **`@Archivable` (Class Level)**:
        - [ ] Is the entity class annotated with `@Archivable`?
        - [ ] Are `nodeName`, `formType`, `viewTech`, and `archiveVersion` correctly defined?
    - [ ] **`@ArchiveProperty` (Field/Method Level)**:
        - [ ] Is `@ArchiveProperty` used for fields that require special handling (e.g., custom date/number format, ignoring a field)?
        - [ ] Is `embeddable=true` used for child objects that should be included in the XML?
- [ ] **Caching**:
    - [ ] Is `@Cache` used for frequently read entities?
    - [ ] Is the concurrency strategy `CacheConcurrencyStrategy.READ_WRITE`?
    - [ ] Is a specific cache `region` defined?
- [ ] **Transient Fields**: Are non-persistent fields marked with `@Transient`?

## 5. Class Body and Methods

- [ ] **Constructors**: Is a no-argument constructor present?
- [ ] **Getters and Setters**: Are standard getters and setters provided for all persistent fields?
- [ ] **`equals()` and `hashCode()`**: Are these methods implemented based on the primary key?
- [ ] **Helper Methods**: Are there helper methods to encapsulate simple business logic?
- [ ] **`toString()`**: Is a `toString()` method provided for logging?
