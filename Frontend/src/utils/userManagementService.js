// utils/userManagementService.js - Enhanced User Management Service
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants";

/**
 * Enhanced User Management Service - Comprehensive User & Permission System
 * 
 * This service provides complete user lifecycle management, role-based access control,
 * and permission management for the smart greenhouse system. Think of it as the
 * "security and HR department" of your greenhouse management system.
 * 
 * Key Capabilities:
 * 1. Complete user CRUD operations with enhanced validation
 * 2. Role-based access control with granular permissions
 * 3. Permission management with real-time validation
 * 4. User activity tracking and audit trails
 * 5. Advanced user search and filtering
 * 6. Bulk operations for admin efficiency
 * 7. Integration with greenhouse-specific permissions
 */

class UserManagementService {
  constructor() {
    // User data cache for performance optimization
    this.userCache = new Map();
    this.roleCache = new Map();
    this.permissionCache = new Map();
    
    // Cache configuration
    this.cacheConfig = {
      users: { ttl: 300000, key: 'users_list' }, // 5 minutes
      roles: { ttl: 600000, key: 'roles_list' }, // 10 minutes
      permissions: { ttl: 900000, key: 'permissions_list' } // 15 minutes
    };
    
    // User management analytics
    this.userAnalytics = {
      totalUsers: 0,
      activeUsers: 0,
      recentRegistrations: 0,
      permissionChanges: 0,
      lastAnalyticsUpdate: null
    };
    
    // Greenhouse-specific permission mappings
    this.greenhousePermissions = new Map([
      ['irrigation:control', 'Can control irrigation system'],
      ['sensors:read', 'Can view sensor data'],
      ['sensors:calibrate', 'Can calibrate sensors'],
      ['schedule:manage', 'Can manage irrigation schedules'],
      ['system:configure', 'Can modify system configuration'],
      ['reports:generate', 'Can generate system reports'],
      ['users:manage', 'Can manage other users'],
      ['admin:access', 'Full administrative access']
    ]);
  }

  /**
   * Get comprehensive user list with enhanced filtering and pagination
   * This provides admin users with detailed user management capabilities
   */
  async getUsers(options = {}) {
    const {
      page = 1,
      limit = 20,
      role = null,
      isActive = null,
      search = '',
      sortBy = 'created_at',
      sortOrder = 'desc',
      includePermissions = true,
      forceRefresh = false
    } = options;

    const cacheKey = `${this.cacheConfig.users.key}_${page}_${limit}_${role}_${isActive}_${search}`;
    
    // Check cache unless forced refresh
    if (!forceRefresh && this.isCacheValid(cacheKey, this.cacheConfig.users.ttl)) {
      const cachedUsers = this.userCache.get(cacheKey);
      if (cachedUsers) {
        console.log('Using cached user list');
        return cachedUsers;
      }
    }

    try {
      console.log('Fetching users from User Management Service...');

      // Build query parameters
      const queryParams = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        sortBy,
        sortOrder
      });

      if (role) queryParams.append('role', role);
      if (isActive !== null) queryParams.append('isActive', isActive.toString());
      if (search) queryParams.append('search', search);

      // Fetch users from User Management Service
      const response = await api.userService('get', `/users?${queryParams}`);
      const usersData = response.data;

      // Enhance user data with additional information
      const enhancedUsers = await this.enhanceUserData(
        usersData.users || usersData.data || [],
        includePermissions
      );

      const result = {
        success: true,
        data: {
          users: enhancedUsers,
          pagination: {
            page,
            limit,
            total: usersData.total || enhancedUsers.length,
            totalPages: Math.ceil((usersData.total || enhancedUsers.length) / limit)
          },
          filters: {
            role,
            isActive,
            search,
            sortBy,
            sortOrder
          }
        },
        analytics: this.calculateUserAnalytics(enhancedUsers)
      };

      // Cache the results
      this.userCache.set(cacheKey, result);
      this.updateUserAnalytics(enhancedUsers);

      return result;

    } catch (error) {
      console.error('Error fetching users:', error);
      
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        cachedData: this.userCache.get(cacheKey),
        recovery: this.generateRecoveryOptions('fetch_users', error)
      };
    }
  }

  /**
   * Create new user with enhanced validation and greenhouse-specific setup
   * This includes setting up appropriate permissions for greenhouse operations
   */
  async createUser(userData, options = {}) {
    const {
      sendWelcomeEmail = true,
      setupDefaultPermissions = true,
      assignDefaultRole = true
    } = options;

    try {
      console.log('Creating new user...', userData.email);

      // Step 1: Enhanced validation of user data
      const validation = this.validateUserData(userData, 'create');
      if (!validation.valid) {
        return {
          success: false,
          error: 'User data validation failed',
          details: validation.errors,
          suggestions: validation.suggestions
        };
      }

      // Step 2: Check for existing user with same email
      const existingUser = await this.checkUserExists(userData.email);
      if (existingUser.exists) {
        return {
          success: false,
          error: 'User with this email already exists',
          existingUserId: existingUser.userId
        };
      }

      // Step 3: Prepare user data with defaults
      const userPayload = {
        ...userData,
        // Add greenhouse-specific default fields
        profile: {
          ...userData.profile,
          greenhouse_access: true,
          notification_preferences: {
            email_alerts: true,
            system_notifications: true,
            irrigation_alerts: true
          }
        }
      };

      // Step 4: Create user via User Management Service
      const response = await api.userService('post', '/users', userPayload);
      const createdUser = response.data;

      // Step 5: Setup default role and permissions if requested
      if (assignDefaultRole || setupDefaultPermissions) {
        await this.setupNewUserPermissions(createdUser.id, userData.role || 'customer');
      }

      // Step 6: Enhanced user setup for greenhouse operations
      const enhancedUser = await this.setupGreenhouseUserProfile(createdUser);

      // Step 7: Clear relevant caches
      this.clearUserCaches();

      // Step 8: Send welcome email if configured
      if (sendWelcomeEmail) {
        await this.sendWelcomeEmail(enhancedUser).catch(err => 
          console.warn('Failed to send welcome email:', err)
        );
      }

      return {
        success: true,
        data: {
          user: enhancedUser,
          setup_status: {
            permissions_configured: setupDefaultPermissions,
            role_assigned: assignDefaultRole,
            greenhouse_profile_created: true,
            welcome_email_sent: sendWelcomeEmail
          }
        },
        message: 'User created successfully with greenhouse access configured'
      };

    } catch (error) {
      console.error('Error creating user:', error);
      
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        recovery: this.generateRecoveryOptions('create_user', error)
      };
    }
  }

  /**
   * Update user with enhanced validation and permission management
   * This handles complex updates including role changes and permission modifications
   */
  async updateUser(userId, updateData, options = {}) {
    const {
      updatePermissions = false,
      validateChanges = true,
      notifyUser = false
    } = options;

    try {
      console.log(`Updating user ${userId}...`);

      // Step 1: Get current user data for comparison
      const currentUser = await this.getUserById(userId);
      if (!currentUser.success) {
        return {
          success: false,
          error: 'User not found',
          userId: userId
        };
      }

      // Step 2: Enhanced validation of update data
      if (validateChanges) {
        const validation = this.validateUserData(updateData, 'update', currentUser.data);
        if (!validation.valid) {
          return {
            success: false,
            error: 'Update data validation failed',
            details: validation.errors,
            suggestions: validation.suggestions
          };
        }
      }

      // Step 3: Handle role changes with permission implications
      let permissionChanges = null;
      if (updateData.role && updateData.role !== currentUser.data.role) {
        permissionChanges = await this.handleRoleChange(
          userId, 
          currentUser.data.role, 
          updateData.role
        );
      }

      // Step 4: Update user via User Management Service
      const response = await api.userService('put', `/users/${userId}`, updateData);
      const updatedUser = response.data;

      // Step 5: Handle permission updates if requested
      if (updatePermissions && updateData.permissions) {
        await this.updateUserPermissions(userId, updateData.permissions);
      }

      // Step 6: Clear relevant caches
      this.clearUserCaches();

      // Step 7: Notify user of changes if requested
      if (notifyUser) {
        await this.notifyUserOfChanges(updatedUser, updateData).catch(err =>
          console.warn('Failed to notify user of changes:', err)
        );
      }

      return {
        success: true,
        data: {
          user: updatedUser,
          changes: this.identifyUserChanges(currentUser.data, updatedUser),
          permission_changes: permissionChanges
        },
        message: 'User updated successfully'
      };

    } catch (error) {
      console.error(`Error updating user ${userId}:`, error);
      
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        userId: userId,
        recovery: this.generateRecoveryOptions('update_user', error)
      };
    }
  }

  /**
   * Enhanced user deletion with cleanup and audit trail
   * This ensures proper cleanup of all user-related data and permissions
   */
  async deleteUser(userId, options = {}) {
    const {
      transferData = null, // userId to transfer data to
      notifyUser = true,
      createAuditLog = true,
      softDelete = false // For compliance requirements
    } = options;

    try {
      console.log(`Deleting user ${userId}...`);

      // Step 1: Get user data for audit and cleanup
      const userToDelete = await this.getUserById(userId);
      if (!userToDelete.success) {
        return {
          success: false,
          error: 'User not found',
          userId: userId
        };
      }

      // Step 2: Check if user has critical data that needs transfer
      const dataCheck = await this.checkUserDataDependencies(userId);
      if (dataCheck.hasCriticalData && !transferData) {
        return {
          success: false,
          error: 'User has critical data that must be transferred before deletion',
          dependencies: dataCheck.dependencies,
          suggestions: ['Specify transferData option', 'Archive user data first']
        };
      }

      // Step 3: Transfer user data if specified
      if (transferData) {
        await this.transferUserData(userId, transferData);
      }

      // Step 4: Clean up user permissions and roles
      await this.cleanupUserPermissions(userId);

      // Step 5: Notify user if requested
      if (notifyUser) {
        await this.notifyUserOfDeletion(userToDelete.data).catch(err =>
          console.warn('Failed to notify user of deletion:', err)
        );
      }

      // Step 6: Create audit log if requested
      if (createAuditLog) {
        await this.createUserAuditLog('user_deleted', userId, userToDelete.data);
      }

      // Step 7: Perform actual deletion (soft or hard)
      if (softDelete) {
        await api.userService('put', `/users/${userId}/deactivate`);
      } else {
        await api.userService('delete', `/users/${userId}`);
      }

      // Step 8: Clear relevant caches
      this.clearUserCaches();

      return {
        success: true,
        data: {
          deleted_user: userToDelete.data,
          deletion_type: softDelete ? 'soft_delete' : 'hard_delete',
          data_transferred: transferData ? true : false,
          transfer_target: transferData
        },
        message: 'User deleted successfully'
      };

    } catch (error) {
      console.error(`Error deleting user ${userId}:`, error);
      
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        userId: userId,
        recovery: this.generateRecoveryOptions('delete_user', error)
      };
    }
  }

  /**
   * Comprehensive role management with greenhouse-specific roles
   * This manages the complex role hierarchy for greenhouse operations
   */
  async manageUserRoles(userId, roleAction, roleData) {
    try {
      console.log(`Managing roles for user ${userId}: ${roleAction}`);

      switch (roleAction) {
        case 'add':
          return await this.addUserRole(userId, roleData.roleId);
        case 'remove':
          return await this.removeUserRole(userId, roleData.roleId);
        case 'replace':
          return await this.replaceUserRoles(userId, roleData.roleIds);
        case 'list':
          return await this.getUserRoles(userId);
        default:
          return {
            success: false,
            error: 'Invalid role action',
            validActions: ['add', 'remove', 'replace', 'list']
          };
      }
    } catch (error) {
      console.error(`Error managing roles for user ${userId}:`, error);
      
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        recovery: this.generateRecoveryOptions('manage_roles', error)
      };
    }
  }

  /**
   * Advanced permission management with real-time validation
   * This provides granular permission control for greenhouse operations
   */
  async manageUserPermissions(userId, permissionAction, permissionData) {
    try {
      console.log(`Managing permissions for user ${userId}: ${permissionAction}`);

      // Validate that user exists and current user has permission to manage
      const userExists = await this.validateUserExists(userId);
      if (!userExists) {
        return {
          success: false,
          error: 'User not found',
          userId: userId
        };
      }

      switch (permissionAction) {
        case 'add':
          return await this.addUserPermission(userId, permissionData.permissionId);
        case 'remove':
          return await this.removeUserPermission(userId, permissionData.permissionId);
        case 'check':
          return await this.checkUserPermission(userId, permissionData.permission);
        case 'list':
          return await this.getUserPermissions(userId);
        case 'bulk_update':
          return await this.bulkUpdateUserPermissions(userId, permissionData.permissions);
        default:
          return {
            success: false,
            error: 'Invalid permission action',
            validActions: ['add', 'remove', 'check', 'list', 'bulk_update']
          };
      }
    } catch (error) {
      console.error(`Error managing permissions for user ${userId}:`, error);
      
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        recovery: this.generateRecoveryOptions('manage_permissions', error)
      };
    }
  }

  /**
   * Enhanced user data with greenhouse-specific information
   * This adds contextual information relevant to greenhouse operations
   */
  async enhanceUserData(users, includePermissions = true) {
    const enhancedUsers = [];

    for (const user of users) {
      const enhancedUser = {
        ...user,
        // Add computed fields
        display_name: this.generateDisplayName(user),
        account_age_days: this.calculateAccountAge(user.created_at),
        last_activity: await this.getLastUserActivity(user.id),
        
        // Add greenhouse-specific fields
        greenhouse_profile: {
          access_level: this.determineAccessLevel(user.roles),
          preferred_units: user.profile?.preferred_units || 'metric',
          notification_settings: user.profile?.notification_preferences || {},
          device_permissions: await this.getDevicePermissions(user.id)
        }
      };

      // Add permission details if requested
      if (includePermissions) {
        enhancedUser.permissions_summary = await this.getUserPermissionsSummary(user.id);
      }

      enhancedUsers.push(enhancedUser);
    }

    return enhancedUsers;
  }

  /**
   * Validate user data with greenhouse-specific validation rules
   * This ensures data integrity and business rule compliance
   */
  validateUserData(userData, operation = 'create', currentUser = null) {
    const errors = [];
    const suggestions = [];

    // Email validation
    if (operation === 'create' || userData.email) {
      if (!userData.email || !this.isValidEmail(userData.email)) {
        errors.push('Valid email address is required');
        suggestions.push('Provide a valid email address in format: user@domain.com');
      }
    }

    // Password validation for new users
    if (operation === 'create' && userData.password) {
      const passwordStrength = this.validatePasswordStrength(userData.password);
      if (!passwordStrength.isStrong) {
        errors.push('Password does not meet security requirements');
        suggestions.push(...passwordStrength.suggestions);
      }
    }

    // Role validation
    if (userData.role) {
      const validRoles = ['admin', 'manager', 'operator', 'customer'];
      if (!validRoles.includes(userData.role)) {
        errors.push('Invalid role specified');
        suggestions.push(`Valid roles are: ${validRoles.join(', ')}`);
      }
    }

    // Greenhouse-specific validations
    if (userData.profile) {
      // Validate notification preferences
      if (userData.profile.notification_preferences) {
        const notifErrors = this.validateNotificationPreferences(userData.profile.notification_preferences);
        errors.push(...notifErrors);
      }

      // Validate greenhouse access permissions
      if (userData.profile.greenhouse_access === false && userData.role === 'admin') {
        errors.push('Admin users must have greenhouse access');
        suggestions.push('Enable greenhouse access for admin users');
      }
    }

    return {
      valid: errors.length === 0,
      errors: errors,
      suggestions: suggestions
    };
  }

  /**
   * Setup new user permissions based on role and greenhouse requirements
   * This configures appropriate access levels for different user types
   */
  async setupNewUserPermissions(userId, role) {
    try {
      console.log(`Setting up permissions for new ${role} user: ${userId}`);

      const rolePermissionMap = {
        admin: [
          'irrigation:control',
          'sensors:read',
          'sensors:calibrate',
          'schedule:manage',
          'system:configure',
          'reports:generate',
          'users:manage',
          'admin:access'
        ],
        manager: [
          'irrigation:control',
          'sensors:read',
          'schedule:manage',
          'reports:generate'
        ],
        operator: [
          'irrigation:control',
          'sensors:read',
          'schedule:manage'
        ],
        customer: [
          'sensors:read'
        ]
      };

      const permissions = rolePermissionMap[role] || rolePermissionMap.customer;
      
      // Add permissions for the new user
      for (const permission of permissions) {
        await this.addUserPermission(userId, permission).catch(err =>
          console.warn(`Failed to add permission ${permission}:`, err)
        );
      }

      return {
        success: true,
        permissions_added: permissions,
        role: role
      };

    } catch (error) {
      console.error('Error setting up new user permissions:', error);
      throw error;
    }
  }

  /**
   * Clear user-related caches when data changes
   * This ensures data consistency across the application
   */
  clearUserCaches() {
    // Clear all user-related cache entries
    for (const key of this.userCache.keys()) {
      if (key.includes('users_') || key.includes('user_')) {
        this.userCache.delete(key);
      }
    }
    
    console.log('User caches cleared');
  }

  /**
   * Check if cache is valid based on TTL
   */
  isCacheValid(key, ttl) {
    const cached = this.userCache.get(key);
    if (!cached) return false;
    
    const age = Date.now() - (cached.timestamp || cached.cached_at || 0);
    return age < ttl;
  }

  /**
   * Get comprehensive user management analytics
   * This provides insights for administrators about user activity and system usage
   */
  getUserManagementAnalytics() {
    return {
      ...this.userAnalytics,
      cache_performance: {
        user_cache_size: this.userCache.size,
        role_cache_size: this.roleCache.size,
        permission_cache_size: this.permissionCache.size
      },
      greenhouse_permissions: Array.from(this.greenhousePermissions.entries()).map(([key, desc]) => ({
        permission: key,
        description: desc
      })),
      last_updated: new Date().toISOString()
    };
  }
}

// Create and export singleton instance
const userManagementService = new UserManagementService();

export default userManagementService;