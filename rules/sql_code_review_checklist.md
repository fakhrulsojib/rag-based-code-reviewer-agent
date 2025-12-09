# SQL Migration Checklist

## 1. Directory and File Structure

- [ ] **Organization**: Are the scripts placed in the correct release version directory (e.g., `/<year>/<version>/`)?
- [ ] **File Naming Convention**: Is the standard file set used (`pre-ddl.sql`, `dml.sql`, `post-ddl.sql`, `sequence.sql`, `backup.sql`)?

## 2. DDL (Data Definition Language) Patterns

- [ ] **`pre-ddl.sql` for Initial Schema Changes**: Are all `CREATE TABLE`, `ALTER TABLE ADD ...`, `CREATE INDEX`, and `CREATE VIEW` statements in this file?
- [ ] **Adding Columns**: If a new column will be `NOT NULL`, is it added as nullable first?
- [ ] **Table and Column Naming**: Are all table, column, and constraint names in snake_case?
- [ ] **Constraints**: Are foreign key and other constraints defined with explicit, meaningful names?

- [ ] **`post-ddl.sql` for Final Schema Tightening**: Does this file primarily contain `ALTER TABLE ... MODIFY ...` statements?
- [ ] **`NOT NULL` Constraint**: Is the `NOT NULL` constraint added in this file after the column has been populated in `dml.sql`?

## 3. DML (Data Manipulation Language) Patterns

- [ ] **`dml.sql` for All Data Changes**: Are all `INSERT`, `UPDATE`, and `DELETE` statements in this file?
- [ ] **Populating New Columns**: Are `UPDATE` statements used to populate new columns?
- [ ] **Complex Updates**: Are subqueries in `UPDATE` statements efficient and using indexes where possible?
- [ ] **Inserting System/Seed Data**: When inserting system data, is the `created_by_id` selected from the `login` table for `therap_system`? Is `SYSTIMESTAMP` used for dates?

## 4. General SQL Style and Best Practices

- [ ] **Comments**: Are comments (`--`) used to denote the module?
- [ ] **Keywords**: Are all SQL keywords in uppercase?
- [ ] **Formatting**: Is the script consistently indented and readable?
- [ ] **Performance**: Have the performance implications of the scripts been considered, especially for large tables?
