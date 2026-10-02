import {defineType, defineField} from 'sanity'

export const incident = defineType({
  name: 'incident',
  title: 'Incident',
  type: 'document',
  fields: [
    defineField({name: 'title', type: 'string'}),
    defineField({name: 'service', type: 'string'}),
    defineField({
      name: 'status',
      type: 'string',
      options: {
        list: ['awaiting_approval', 'approved', 'rejected', 'verified', 'failed'],
        layout: 'radio',
      },
      initialValue: 'awaiting_approval',
    }),
    defineField({name: 'diagnosis', type: 'text'}),
    defineField({name: 'action', type: 'string'}),
    defineField({name: 'risk', type: 'string'}),
    defineField({name: 'logExcerpt', type: 'text'}),
    defineField({name: 'result', type: 'text'}),
    defineField({name: 'detectedAt', type: 'datetime'}),
    defineField({name: 'resolvedAt', type: 'datetime'}),
  ],
})
