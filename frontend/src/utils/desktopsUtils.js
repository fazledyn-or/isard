import { cardIcons } from '../shared/constants'

export class DesktopUtils {
  static parseDesktops (items) {
    return items.map((item) => {
      const { description, icon, id, name, state, type, viewers, ip, template } = item
      return {
        description,
        icon: !icon || !(icon in cardIcons) ? 'default' : icon,
        id,
        name,
        state,
        type,
        ip,
        viewers,
        template
      }
    }) || []
  }

  static parseTemplates (items) {
    return items.map((item) => {
      const { description, icon, id, name } = item
      return {
        description,
        icon: !icon || !(icon in cardIcons) ? 'default' : icon,
        id,
        name
      }
    }) || []
  }
}
