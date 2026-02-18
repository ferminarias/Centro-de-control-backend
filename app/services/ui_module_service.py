"""
Service layer for UI Module management.
Handles module registration, permission checking, and synchronization.
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.ui_module import RoleModulePermission, UIModule


class UIModuleService:
    """Service for managing UI modules and permissions."""

    # Default system modules that are available to all accounts
    DEFAULT_MODULES: list[dict[str, Any]] = [
        {
            "codigo": "fields",
            "nombre": "Datos",
            "descripcion": "Gestión de campos personalizados",
            "ruta": "/fields",
            "icono": "Database",
            "orden": 1,
            "acciones": {
                "view": {"label": "Ver", "description": "Ver campos personalizados"},
                "create": {"label": "Crear", "description": "Crear nuevos campos"},
                "edit": {"label": "Editar", "description": "Editar campos existentes"},
                "delete": {"label": "Eliminar", "description": "Eliminar campos"},
            },
        },
        {
            "codigo": "leads",
            "nombre": "Leads",
            "descripcion": "Gestión de leads y contactos",
            "ruta": "/leads",
            "icono": "Users",
            "orden": 2,
            "acciones": {
                "view": {"label": "Ver", "description": "Ver lista de leads"},
                "create": {"label": "Crear", "description": "Crear nuevos leads"},
                "edit": {"label": "Editar", "description": "Editar leads"},
                "delete": {"label": "Eliminar", "description": "Eliminar leads"},
                "export": {"label": "Exportar", "description": "Exportar leads a Excel"},
                "import": {"label": "Importar", "description": "Importar leads desde Excel"},
            },
        },
        {
            "codigo": "bases",
            "nombre": "Bases",
            "descripcion": "Gestión de bases de datos",
            "ruta": "/bases",
            "icono": "HardDrive",
            "orden": 3,
            "es_submodulo": False,
            "acciones": {
                "view": {"label": "Ver", "description": "Ver bases de datos"},
                "create": {"label": "Crear", "description": "Crear nuevas bases"},
                "edit": {"label": "Editar", "description": "Editar bases"},
                "delete": {"label": "Eliminar", "description": "Eliminar bases"},
            },
        },
        {
            "codigo": "datasources",
            "nombre": "DataSources",
            "descripcion": "Configuración de fuentes de datos",
            "ruta": "/datasources",
            "icono": "GitBranch",
            "orden": 4,
            "es_submodulo": True,
            "parent_code": "bases",
            "acciones": {
                "view": {"label": "Ver", "description": "Ver fuentes de datos"},
                "create": {"label": "Crear", "description": "Crear nuevas fuentes"},
                "edit": {"label": "Editar", "description": "Editar fuentes"},
                "delete": {"label": "Eliminar", "description": "Eliminar fuentes"},
            },
        },
        {
            "codigo": "move_leads",
            "nombre": "Mover Leads",
            "descripcion": "Mover leads entre bases",
            "ruta": "/move-leads",
            "icono": "ArrowRightLeft",
            "orden": 5,
            "es_submodulo": True,
            "parent_code": "bases",
            "acciones": {
                "view": {"label": "Ver", "description": "Acceder a mover leads"},
                "execute": {"label": "Ejecutar", "description": "Mover leads entre bases"},
            },
        },
    ]

    def __init__(self, db: Session):
        self.db = db

    def get_modules(
        self,
        cuenta_id: uuid.UUID | None = None,
        include_system: bool = True,
    ) -> list[UIModule]:
        """Get modules for an account, optionally including system modules."""
        query = self.db.query(UIModule)

        if cuenta_id and include_system:
            query = query.filter(
                (UIModule.cuenta_id == cuenta_id) | (UIModule.es_sistema.is_(True))
            )
        elif cuenta_id:
            query = query.filter(UIModule.cuenta_id == cuenta_id)
        elif include_system:
            query = query.filter(UIModule.es_sistema.is_(True))
        else:
            return []

        return query.order_by(UIModule.orden, UIModule.nombre).all()

    def get_module_by_code(
        self,
        codigo: str,
        cuenta_id: uuid.UUID | None = None,
    ) -> UIModule | None:
        """Get a module by its code."""
        query = self.db.query(UIModule).filter(UIModule.codigo == codigo)

        if cuenta_id:
            query = query.filter(
                (UIModule.cuenta_id == cuenta_id) | (UIModule.es_sistema.is_(True))
            )

        return query.first()

    def sync_modules(
        self,
        cuenta_id: uuid.UUID | None,
        modules_data: list[dict[str, Any]],
    ) -> list[UIModule]:
        """Synchronize modules from frontend registry.

        Creates new modules, updates existing ones, and deactivates removed ones.
        """
        existing_modules = {
            m.codigo: m
            for m in self.get_modules(cuenta_id=cuenta_id, include_system=False)
        }

        processed_codes = set()
        result = []

        for module_data in modules_data:
            codigo = module_data["codigo"]
            processed_codes.add(codigo)

            existing = existing_modules.get(codigo)

            if existing:
                # Update existing module
                existing.nombre = module_data.get("nombre", existing.nombre)
                existing.descripcion = module_data.get("descripcion", existing.descripcion)
                existing.ruta = module_data.get("ruta", existing.ruta)
                existing.icono = module_data.get("icono", existing.icono)
                existing.orden = module_data.get("orden", existing.orden)
                existing.acciones = module_data.get("acciones", existing.acciones)
                existing.es_submodulo = module_data.get("es_submodulo", existing.es_submodulo)
                existing.parent_code = module_data.get("parent_code", existing.parent_code)
                result.append(existing)
            else:
                # Create new module
                new_module = UIModule(
                    cuenta_id=cuenta_id,
                    codigo=codigo,
                    nombre=module_data["nombre"],
                    descripcion=module_data.get("descripcion"),
                    ruta=module_data["ruta"],
                    icono=module_data.get("icono"),
                    orden=module_data.get("orden", 0),
                    es_submodulo=module_data.get("es_submodulo", False),
                    parent_code=module_data.get("parent_code"),
                    acciones=module_data.get("acciones", {}),
                    es_sistema=False,
                )
                self.db.add(new_module)
                result.append(new_module)

        self.db.flush()
        return result

    def initialize_system_modules(self) -> list[UIModule]:
        """Initialize default system modules."""
        return self.sync_modules(None, self.DEFAULT_MODULES)

    def get_role_permissions(
        self,
        role_id: uuid.UUID,
    ) -> dict[str, list[str]]:
        """Get all module permissions for a role.

        Returns a dict mapping module_code -> list of allowed actions.
        """
        permissions = (
            self.db.query(RoleModulePermission)
            .filter(RoleModulePermission.role_id == role_id)
            .all()
        )

        result = {}
        for perm in permissions:
            if perm.module and perm.module.codigo:
                result[perm.module.codigo] = perm.acciones_permitidas

        return result

    def set_role_permissions(
        self,
        role_id: uuid.UUID,
        module_id: uuid.UUID,
        acciones_permitidas: list[str],
    ) -> RoleModulePermission:
        """Set permissions for a role on a specific module."""
        # Check if permission entry exists
        perm = (
            self.db.query(RoleModulePermission)
            .filter(
                RoleModulePermission.role_id == role_id,
                RoleModulePermission.module_id == module_id,
            )
            .first()
        )

        if perm:
            perm.acciones_permitidas = acciones_permitidas
        else:
            perm = RoleModulePermission(
                role_id=role_id,
                module_id=module_id,
                acciones_permitidas=acciones_permitidas,
            )
            self.db.add(perm)

        self.db.flush()
        return perm

    def delete_role_permissions(
        self,
        role_id: uuid.UUID,
        module_id: uuid.UUID,
    ) -> bool:
        """Delete permissions for a role on a specific module."""
        result = (
            self.db.query(RoleModulePermission)
            .filter(
                RoleModulePermission.role_id == role_id,
                RoleModulePermission.module_id == module_id,
            )
            .delete()
        )
        return result > 0

    def get_user_permissions(
        self,
        user_role_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        """Get complete permissions for a user.

        Returns both legacy permissions and new modular permissions.
        """
        if not user_role_id:
            return {
                "permisos": [],
                "modulos": {},
            }

        role = self.db.query(Role).filter(Role.id == user_role_id).first()
        if not role:
            return {
                "permisos": [],
                "modulos": {},
            }

        # Get legacy permissions
        legacy_perms = role.permisos or []

        # Get modular permissions
        modular_perms = self.get_role_permissions(role.id)

        return {
            "permisos": legacy_perms,
            "modulos": modular_perms,
        }

    def can_perform_action(
        self,
        role_id: uuid.UUID | None,
        module_code: str,
        action: str,
    ) -> bool:
        """Check if a role can perform an action on a module."""
        if not role_id:
            return False

        permissions = self.get_role_permissions(role_id)
        module_perms = permissions.get(module_code, [])

        # Check for wildcard permission
        if "*" in module_perms:
            return True

        return action in module_perms
